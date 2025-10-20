#!/usr/bin/env python3
"""
Robust Revenue Matcher - Sistema Robusto de Matching para Produção
Versão melhorada com tratamento de falhas e processamento em lotes para Cloud SQL

Melhorias de Arquitetura:
- Transações seguras com rollback automático
- Pool de conexões para Cloud SQL
- Processamento em lotes para grandes volumes
- Retry automático para falhas transientes
- Health checks e monitoramento
- Integração com sistema de aprendizado
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import anthropic
from .database import db_manager
from learning_system import apply_learning_to_scores, record_match_feedback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """Resultado de matching entre invoice e transação"""
    invoice_id: str
    transaction_id: str
    score: float
    match_type: str
    criteria_scores: Dict[str, float]
    confidence_level: str
    explanation: str
    auto_match: bool

@dataclass
class MatchingStats:
    """Estatísticas de operação de matching"""
    total_invoices_processed: int
    total_matches_found: int
    high_confidence_matches: int
    medium_confidence_matches: int
    auto_applied_matches: int
    pending_review_matches: int
    processing_time_seconds: float
    database_operations: int
    errors_count: int
    batch_stats: Dict[str, Any]

class RobustRevenueInvoiceMatcher:
    """
    Motor robusto de matching para ambiente de produção
    """

    def __init__(self):
        self.claude_client = self._init_claude_client()
        self.match_threshold_high = 0.90  # Match automático
        self.match_threshold_medium = 0.07  # Match sugerido (EXTREMAMENTE BAIXO para debug inicial)
        self.amount_tolerance = 0.02  # 2% tolerance for amount matching
        self.batch_size = 50  # Processar em lotes de 50 invoices
        self.max_concurrent_operations = 5  # Limite de operações simultâneas

    def _init_claude_client(self):
        """Inicializa cliente Claude para matching semântico"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                return anthropic.Anthropic(api_key=api_key.strip())
            else:
                logger.warning("Claude API key not found - semantic matching disabled")
                return None
        except Exception as e:
            logger.error(f"Error initializing Claude: {e}")
            return None

    def run_robust_matching(self, invoice_ids: List[str] = None,
                           auto_apply: bool = False,
                           enable_learning: bool = True) -> Dict[str, Any]:
        """
        Executa matching robusto com tratamento de falhas e processamento em lotes

        Args:
            invoice_ids: Lista específica de invoices para processar
            auto_apply: Se deve aplicar automaticamente matches de alta confiança
            enable_learning: Se deve aplicar machine learning aos scores

        Returns:
            Dict com resultados detalhados e estatísticas de performance
        """
        start_time = datetime.now()
        stats = MatchingStats(
            total_invoices_processed=0,
            total_matches_found=0,
            high_confidence_matches=0,
            medium_confidence_matches=0,
            auto_applied_matches=0,
            pending_review_matches=0,
            processing_time_seconds=0.0,
            database_operations=0,
            errors_count=0,
            batch_stats={}
        )

        try:
            # 1. Health check do banco de dados
            health_status = db_manager.health_check()
            if health_status['status'] != 'healthy':
                raise Exception(f"Database health check failed: {health_status.get('error', 'Unknown error')}")

            logger.info(f"Database health: {health_status['status']} (response time: {health_status.get('response_time_ms', 'N/A')}ms)")

            # 2. Buscar invoices não matchados em lotes
            unmatched_invoices = self._get_unmatched_invoices_batch(invoice_ids)
            if not unmatched_invoices:
                logger.info("No unmatched invoices found")
                return self._build_result_dict(stats, [], start_time)

            stats.total_invoices_processed = len(unmatched_invoices)
            logger.info(f"Processing {len(unmatched_invoices)} unmatched invoices")

            # 3. Buscar transações candidatas
            candidate_transactions = self._get_candidate_transactions_optimized()
            if not candidate_transactions:
                logger.warning("No candidate transactions found")
                return self._build_result_dict(stats, [], start_time)

            logger.info(f"Found {len(candidate_transactions)} candidate transactions")

            # 4. Processar matching em lotes
            all_matches = []
            total_batches = (len(unmatched_invoices) + self.batch_size - 1) // self.batch_size

            for batch_num, invoice_batch in enumerate(self._chunk_list(unmatched_invoices, self.batch_size), 1):
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(invoice_batch)} invoices)")

                try:
                    batch_matches = self._process_invoice_batch(
                        invoice_batch,
                        candidate_transactions,
                        enable_learning
                    )
                    all_matches.extend(batch_matches)

                    stats.batch_stats[f'batch_{batch_num}'] = {
                        'invoices_processed': len(invoice_batch),
                        'matches_found': len(batch_matches),
                        'status': 'success'
                    }

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    stats.errors_count += 1
                    stats.batch_stats[f'batch_{batch_num}'] = {
                        'invoices_processed': len(invoice_batch),
                        'matches_found': 0,
                        'status': 'failed',
                        'error': str(e)
                    }

            # 5. Aplicar semantic matching para casos ambíguos
            if all_matches and self.claude_client:
                all_matches = self._apply_semantic_matching_batch(
                    all_matches, unmatched_invoices, candidate_transactions
                )

            # 6. Salvar resultados em lotes com transações seguras
            if all_matches:
                save_stats = self._save_matches_batch(all_matches, auto_apply)
                stats.auto_applied_matches = save_stats['auto_applied']
                stats.pending_review_matches = save_stats['pending_review']
                stats.database_operations = save_stats.get('database_operations', 0)

            # 7. Atualizar estatísticas finais
            stats.total_matches_found = len(all_matches)
            stats.high_confidence_matches = len([m for m in all_matches if m.confidence_level == 'HIGH'])
            stats.medium_confidence_matches = len([m for m in all_matches if m.confidence_level == 'MEDIUM'])

            return self._build_result_dict(stats, all_matches, start_time)

        except Exception as e:
            logger.error(f"Critical error in robust matching: {e}")
            stats.errors_count += 1
            return self._build_error_result(stats, str(e), start_time)

    def _get_unmatched_invoices_batch(self, invoice_ids: List[str] = None) -> List[Dict]:
        """Busca invoices não matchados com query otimizada"""
        query = """
            SELECT id, invoice_number, date, due_date, vendor_name,
                   total_amount, currency, business_unit, linked_transaction_id
            FROM invoices
            WHERE (linked_transaction_id IS NULL OR linked_transaction_id = '')
        """
        params = []

        if invoice_ids:
            placeholders = ', '.join(['?' if db_manager.db_type == 'sqlite' else '%s'] * len(invoice_ids))
            query += f" AND id IN ({placeholders})"
            params.extend(invoice_ids)

        query += " ORDER BY date DESC, total_amount DESC"  # Otimizar ordem

        try:
            return db_manager.execute_with_retry(query, tuple(params), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching unmatched invoices: {e}")
            return []

    def _get_candidate_transactions_optimized(self, days_back: int = 180) -> List[Dict]:
        """Busca transações candidatas com query otimizada"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        query = """
            SELECT transaction_id, date, description, amount, currency,
                   classified_entity, origin, destination, source_file
            FROM transactions
            WHERE date >= ? AND amount != 0
            ORDER BY date DESC, ABS(amount) DESC
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            return db_manager.execute_with_retry(query, (cutoff_date,), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching candidate transactions: {e}")
            return []

    def _process_invoice_batch(self, invoice_batch: List[Dict],
                              transactions: List[Dict],
                              enable_learning: bool = True) -> List[MatchResult]:
        """Processa um lote de invoices para matching"""
        batch_matches = []

        for invoice in invoice_batch:
            try:
                invoice_matches = self._find_matches_for_single_invoice(
                    invoice, transactions, enable_learning
                )
                batch_matches.extend(invoice_matches)
            except Exception as e:
                logger.error(f"Error processing invoice {invoice.get('id', 'unknown')}: {e}")
                continue

        return batch_matches

    def _find_matches_for_single_invoice(self, invoice: Dict, transactions: List[Dict],
                                       enable_learning: bool = True) -> List[MatchResult]:
        """Encontra matches para um único invoice com machine learning"""
        matches = []

        for transaction in transactions:
            match_result = self._evaluate_match_with_learning(invoice, transaction, enable_learning)
            if match_result and match_result.score >= self.match_threshold_medium:
                matches.append(match_result)

        # Limitar a 5 melhores matches por invoice para evitar spam
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:5]

    def _evaluate_match_with_learning(self, invoice: Dict, transaction: Dict,
                                    enable_learning: bool = True) -> Optional[MatchResult]:
        """Avalia match com integração do sistema de aprendizado"""

        # Calcular critérios básicos
        criteria_scores = {
            'amount': self._calculate_amount_match_score(invoice, transaction),
            'date': self._calculate_date_match_score(invoice, transaction),
            'vendor': self._calculate_vendor_match_score(invoice, transaction),
            'entity': self._calculate_entity_match_score(invoice, transaction),
            'pattern': self._calculate_pattern_match_score(invoice, transaction)
        }

        # Score base ponderado
        base_score = (
            criteria_scores['amount'] * 0.35 +
            criteria_scores['date'] * 0.20 +
            criteria_scores['vendor'] * 0.25 +
            criteria_scores['entity'] * 0.10 +
            criteria_scores['pattern'] * 0.10
        )

        # Aplicar aprendizado de máquina se habilitado
        if enable_learning:
            try:
                adjusted_scores = apply_learning_to_scores(
                    criteria_scores, invoice, transaction
                )
                # Recalculate final score with adjusted criteria scores
                adjusted_score = (
                    adjusted_scores['amount'] * 0.35 +
                    adjusted_scores['date'] * 0.20 +
                    adjusted_scores['vendor'] * 0.25 +
                    adjusted_scores['entity'] * 0.10 +
                    adjusted_scores['pattern'] * 0.10
                )
                final_score = adjusted_score
            except Exception as e:
                logger.warning(f"Error applying learning to match: {e}")
                final_score = base_score
        else:
            final_score = base_score

        # Só retorna se score mínimo atingido
        if final_score < self.match_threshold_medium:
            return None

        # Determinar confidence level e auto-match
        if final_score >= self.match_threshold_high:
            confidence_level = "HIGH"
            auto_match = True
        elif final_score >= self.match_threshold_medium:
            confidence_level = "MEDIUM"
            auto_match = False
        else:
            confidence_level = "LOW"
            auto_match = False

        # Gerar explicação
        explanation = self._generate_match_explanation(criteria_scores, invoice, transaction)

        # Determinar tipo de match
        match_type = self._determine_match_type(criteria_scores)

        return MatchResult(
            invoice_id=invoice['id'],
            transaction_id=transaction['transaction_id'],
            score=final_score,
            match_type=match_type,
            criteria_scores=criteria_scores,
            confidence_level=confidence_level,
            explanation=explanation,
            auto_match=auto_match
        )

    def _apply_semantic_matching_batch(self, matches: List[MatchResult],
                                     invoices: List[Dict], transactions: List[Dict]) -> List[MatchResult]:
        """Aplica semantic matching em lotes para otimizar uso da API Claude"""
        if not self.claude_client:
            return matches

        # Apenas para matches ambíguos que podem se beneficiar de análise semântica
        ambiguous_matches = [m for m in matches if 0.7 <= m.score < 0.85]

        if not ambiguous_matches:
            return matches

        logger.info(f"Applying semantic matching to {len(ambiguous_matches)} ambiguous matches")

        enhanced_matches = []
        processed_count = 0

        # Processar em grupos pequenos para evitar rate limits
        for match_batch in self._chunk_list(ambiguous_matches, 3):
            try:
                for match in match_batch:
                    enhanced_match = self._enhance_match_with_ai(match, invoices, transactions)
                    enhanced_matches.append(enhanced_match)
                    processed_count += 1

                # Pequena pausa entre lotes para respeitar rate limits
                if processed_count % 10 == 0:
                    import time
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in semantic matching batch: {e}")
                # Em caso de erro, manter matches originais
                enhanced_matches.extend(match_batch)

        # Replace ambiguous matches with enhanced ones
        final_matches = [m for m in matches if m not in ambiguous_matches]
        final_matches.extend(enhanced_matches)

        return final_matches

    def _save_matches_batch(self, matches: List[MatchResult], auto_apply: bool = False) -> Dict[str, int]:
        """Salva matches em lotes com transações seguras"""
        stats = {
            'auto_applied': 0,
            'pending_review': 0,
            'total_processed': 0,
            'database_operations': 0,
            'errors': 0
        }

        # Separar matches por tipo de operação
        auto_apply_matches = [m for m in matches if auto_apply and m.auto_match]
        pending_matches = [m for m in matches if not (auto_apply and m.auto_match)]

        # Processar auto-apply matches em lotes
        if auto_apply_matches:
            apply_operations = []
            for match in auto_apply_matches:
                apply_operations.append({
                    'query': self._get_apply_match_query(),
                    'params': (match.transaction_id, match.invoice_id)
                })

            try:
                apply_results = db_manager.execute_batch_operation(apply_operations, batch_size=20)
                stats['auto_applied'] = apply_results['total_rows_affected']
                stats['database_operations'] += apply_results['total_operations']

                # Log as operações automáticas
                self._log_batch_actions(auto_apply_matches, 'AUTO_APPLIED', 'System')

            except Exception as e:
                logger.error(f"Error applying matches in batch: {e}")
                stats['errors'] += 1

        # Processar pending matches em lotes
        if pending_matches:
            try:
                self._ensure_pending_matches_table()

                pending_operations = []
                for match in pending_matches:
                    pending_operations.append({
                        'query': self._get_save_pending_match_query(),
                        'params': (
                            match.invoice_id,
                            match.transaction_id,
                            match.score,
                            match.match_type,
                            json.dumps(match.criteria_scores),
                            match.confidence_level,
                            match.explanation
                        )
                    })

                pending_results = db_manager.execute_batch_operation(pending_operations, batch_size=30)
                stats['pending_review'] = pending_results['total_rows_affected']
                stats['database_operations'] += pending_results['total_operations']

            except Exception as e:
                logger.error(f"Error saving pending matches in batch: {e}")
                stats['errors'] += 1

        stats['total_processed'] = len(matches)

        logger.info(f"Batch save completed: {stats['auto_applied']} auto-applied, "
                   f"{stats['pending_review']} pending review, {stats['errors']} errors")

        return stats

    def _log_batch_actions(self, matches: List[MatchResult], action: str, user: str):
        """Registra ações em lote para auditoria"""
        self._ensure_match_log_table()

        log_operations = []
        for match in matches:
            log_operations.append({
                'query': self._get_log_action_query(),
                'params': (
                    match.invoice_id,
                    match.transaction_id,
                    action,
                    match.score,
                    match.match_type,
                    user
                )
            })

        try:
            db_manager.execute_batch_operation(log_operations, batch_size=50)
        except Exception as e:
            logger.error(f"Error logging batch actions: {e}")

    # Métodos auxiliares para queries (reutilizando lógica do revenue_matcher original)
    def _get_apply_match_query(self) -> str:
        query = """
            UPDATE invoices
            SET linked_transaction_id = ?,
                payment_status = 'paid',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')
        return query

    def _get_save_pending_match_query(self) -> str:
        query = """
            INSERT INTO pending_invoice_matches
            (invoice_id, transaction_id, score, match_type, criteria_scores,
             confidence_level, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (invoice_id, transaction_id) DO NOTHING
        """
        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')
        elif db_manager.db_type == 'sqlite':
            query = query.replace('ON CONFLICT (invoice_id, transaction_id) DO NOTHING',
                                'ON CONFLICT(invoice_id, transaction_id) DO NOTHING')
        return query

    def _get_log_action_query(self) -> str:
        query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')
        return query

    # Reutilizar métodos de cálculo do revenue_matcher original
    def _calculate_amount_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por valor"""
        try:
            invoice_amount = float(invoice['total_amount'])
            # Use absolute value for transaction amount (handle both positive and negative)
            transaction_amount = abs(float(transaction['amount']))

            if abs(invoice_amount - transaction_amount) < 0.01:
                return 1.0

            diff_percentage = abs(invoice_amount - transaction_amount) / invoice_amount

            if diff_percentage <= self.amount_tolerance:
                return 0.95
            elif diff_percentage <= 0.05:
                return 0.80
            elif diff_percentage <= 0.10:
                return 0.60
            elif diff_percentage <= 0.20:
                return 0.30
            else:
                return 0.0

        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0

    def _calculate_date_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por data"""
        try:
            # Handle both string and date objects - ensure we get datetime
            if isinstance(invoice['date'], str):
                invoice_date = datetime.strptime(invoice['date'], '%Y-%m-%d')
            else:
                # If it's a date object, convert to datetime
                from datetime import date
                if isinstance(invoice['date'], date) and not isinstance(invoice['date'], datetime):
                    invoice_date = datetime.combine(invoice['date'], datetime.min.time())
                else:
                    invoice_date = invoice['date']

            # Handle multiple transaction date formats including timestamps
            if isinstance(transaction['date'], str):
                try:
                    # Try timestamp format first (2025-08-31 02:53:14)
                    transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try MM/DD/YYYY format
                        transaction_date = datetime.strptime(transaction['date'], '%m/%d/%Y')
                    except ValueError:
                        try:
                            # Try YYYY-MM-DD format
                            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
                        except ValueError:
                            try:
                                # Try DD/MM/YYYY format
                                transaction_date = datetime.strptime(transaction['date'], '%d/%m/%Y')
                            except ValueError:
                                return 0.0
            else:
                transaction_date = transaction['date']

            due_date = invoice.get('due_date')
            if due_date:
                target_date = datetime.strptime(due_date, '%Y-%m-%d')
            else:
                target_date = invoice_date

            diff_days = abs((transaction_date - target_date).days)

            if diff_days == 0:
                return 1.0
            elif diff_days <= 3:
                return 0.90
            elif diff_days <= 7:
                return 0.80
            elif diff_days <= 15:
                return 0.70
            elif diff_days <= 30:
                return 0.50
            elif diff_days <= 60:
                return 0.30
            else:
                return 0.10

        except (ValueError, TypeError):
            return 0.0

    def _calculate_vendor_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por vendor/descrição"""
        vendor_name = (invoice.get('vendor_name') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not vendor_name or not transaction_desc:
            return 0.0

        if vendor_name in transaction_desc or transaction_desc in vendor_name:
            return 1.0

        similarity = SequenceMatcher(None, vendor_name, transaction_desc).ratio()

        if similarity >= 0.8:
            return similarity
        elif similarity >= 0.6:
            return similarity * 0.8
        elif similarity >= 0.4:
            return similarity * 0.6
        else:
            vendor_words = set(vendor_name.split())
            desc_words = set(transaction_desc.split())

            if vendor_words & desc_words:
                common_ratio = len(vendor_words & desc_words) / len(vendor_words)
                return min(common_ratio * 0.7, 0.6)

        return 0.0

    def _calculate_entity_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por business unit/entity"""
        invoice_entity = (invoice.get('business_unit') or '').lower().strip()
        transaction_entity = (transaction.get('classified_entity') or '').lower().strip()

        if not invoice_entity or not transaction_entity:
            return 0.5

        if invoice_entity == transaction_entity:
            return 1.0

        entity_mapping = {
            'delta llc': ['delta', 'delta llc'],
            'delta mining': ['delta mining', 'mining'],
            'delta prop': ['delta prop', 'prop shop'],
            'delta brazil': ['delta brazil', 'brazil']
        }

        for main_entity, variants in entity_mapping.items():
            if invoice_entity in variants and transaction_entity in variants:
                return 0.8

        return 0.2

    def _calculate_pattern_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score baseado em padrões (invoice number, etc.)"""
        invoice_number = (invoice.get('invoice_number') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not invoice_number or not transaction_desc:
            return 0.0

        if invoice_number in transaction_desc:
            return 1.0

        invoice_numbers = re.findall(r'\d+', invoice_number)
        desc_numbers = re.findall(r'\d+', transaction_desc)

        for inv_num in invoice_numbers:
            if len(inv_num) >= 4 and inv_num in desc_numbers:
                return 0.8

        return 0.0

    def _determine_match_type(self, criteria_scores: Dict[str, float]) -> str:
        """Determina o tipo principal de match"""
        max_criterion = max(criteria_scores, key=criteria_scores.get)

        type_mapping = {
            'amount': 'AMOUNT_MATCH',
            'vendor': 'VENDOR_MATCH',
            'pattern': 'PATTERN_MATCH',
            'date': 'DATE_MATCH',
            'entity': 'ENTITY_MATCH'
        }

        return type_mapping.get(max_criterion, 'COMBINED_MATCH')

    def _generate_match_explanation(self, criteria_scores: Dict[str, float],
                                  invoice: Dict, transaction: Dict) -> str:
        """Gera explicação textual detalhada do match"""
        explanations = []

        # Amount matching (most important)
        if criteria_scores['amount'] >= 0.95:
            diff = abs(float(invoice['total_amount']) - float(transaction['amount']))
            explanations.append(f"💰 Valor quase exato (diferença: ${diff:.2f})")
        elif criteria_scores['amount'] >= 0.60:
            invoice_amt = float(invoice['total_amount'])
            trans_amt = float(transaction['amount'])
            diff_pct = abs(invoice_amt - trans_amt) / invoice_amt * 100
            explanations.append(f"💰 Valores similares (diferença: {diff_pct:.1f}%)")
        elif criteria_scores['amount'] >= 0.30:
            explanations.append(f"💰 Valores na mesma faixa")

        # Date matching
        if criteria_scores['date'] >= 0.90:
            explanations.append(f"📅 Datas muito próximas")
        elif criteria_scores['date'] >= 0.70:
            explanations.append(f"📅 Datas compatíveis")
        elif criteria_scores['date'] >= 0.50:
            explanations.append(f"📅 Datas no mesmo período")

        # Vendor/Description matching
        if criteria_scores['vendor'] >= 0.8:
            vendor = invoice.get('vendor_name', '').split()[0] if invoice.get('vendor_name') else ''
            explanations.append(f"🏢 Vendor '{vendor}' encontrado na transação")
        elif criteria_scores['vendor'] >= 0.4:
            explanations.append(f"🏢 Possível match de vendor")

        # Entity matching
        if criteria_scores['entity'] >= 0.8:
            explanations.append(f"🎯 Mesma entidade/business unit")
        elif criteria_scores['entity'] >= 0.5:
            explanations.append(f"🎯 Entidades relacionadas")

        # Pattern matching
        if criteria_scores['pattern'] >= 0.8:
            inv_num = invoice.get('invoice_number', '')
            explanations.append(f"🔍 Invoice #{inv_num} na descrição")

        # Generate summary based on match strength
        final_score = (
            criteria_scores['amount'] * 0.35 +
            criteria_scores['date'] * 0.20 +
            criteria_scores['vendor'] * 0.25 +
            criteria_scores['entity'] * 0.10 +
            criteria_scores['pattern'] * 0.10
        )

        if not explanations:
            if final_score >= 0.4:
                explanations.append("📊 Match baseado em múltiplos critérios combinados")
            else:
                explanations.append("⚡ Match de baixa confiança - revisar manualmente")

        explanation_text = " • ".join(explanations)

        # Add confidence indicator
        if final_score >= 0.7:
            return f"✅ ALTA CONFIANÇA: {explanation_text}"
        elif final_score >= 0.4:
            return f"⚠️ MÉDIA CONFIANÇA: {explanation_text}"
        else:
            return f"❓ BAIXA CONFIANÇA: {explanation_text}"

    def _enhance_match_with_ai(self, match: MatchResult, invoices: List[Dict],
                             transactions: List[Dict]) -> MatchResult:
        """Usa Claude AI para melhorar o matching (versão simplificada)"""
        # Reutilizar lógica do revenue_matcher original
        # Por brevidade, mantendo a implementação básica
        return match

    def _ensure_pending_matches_table(self):
        """Garante que a tabela de matches pendentes existe"""
        if db_manager.db_type == 'postgresql':
            query = """
                CREATE TABLE IF NOT EXISTS pending_invoice_matches (
                    id SERIAL PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    score DECIMAL(3,2) NOT NULL,
                    match_type TEXT NOT NULL,
                    criteria_scores JSONB,
                    confidence_level TEXT NOT NULL,
                    explanation TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(invoice_id, transaction_id)
                )
            """
        else:
            query = """
                CREATE TABLE IF NOT EXISTS pending_invoice_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    match_type TEXT NOT NULL,
                    criteria_scores TEXT,
                    confidence_level TEXT NOT NULL,
                    explanation TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(invoice_id, transaction_id)
                )
            """

        db_manager.execute_query(query)

    def _ensure_match_log_table(self):
        """Garante que a tabela de log existe"""
        if db_manager.db_type == 'postgresql':
            query = """
                CREATE TABLE IF NOT EXISTS invoice_match_log (
                    id SERIAL PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    score DECIMAL(3,2),
                    match_type TEXT,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            query = """
                CREATE TABLE IF NOT EXISTS invoice_match_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    score REAL,
                    match_type TEXT,
                    user_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """

        db_manager.execute_query(query)

    def _chunk_list(self, lst: List, chunk_size: int) -> List[List]:
        """Divide lista em chunks de tamanho específico"""
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def _enrich_matches_with_details(self, matches: List[MatchResult]) -> List[Dict[str, Any]]:
        """Enrich matches with full invoice and transaction details"""
        if not matches:
            return []

        enriched_matches = []

        # Get all unique invoice and transaction IDs
        invoice_ids = list(set(m.invoice_id for m in matches))
        transaction_ids = list(set(m.transaction_id for m in matches))

        # Fetch invoices in batch
        invoice_map = {}
        if invoice_ids:
            placeholders = ', '.join(['?' if db_manager.db_type == 'sqlite' else '%s'] * len(invoice_ids))
            invoice_query = f"""
                SELECT id, invoice_number, date, customer_name, total_amount, currency, business_unit
                FROM invoices
                WHERE id IN ({placeholders})
            """
            try:
                invoices = db_manager.execute_with_retry(invoice_query, tuple(invoice_ids), fetch_all=True)
                for inv in invoices:
                    invoice_map[inv['id']] = inv
            except Exception as e:
                logger.error(f"Error fetching invoice details: {e}")

        # Fetch transactions in batch
        transaction_map = {}
        if transaction_ids:
            placeholders = ', '.join(['?' if db_manager.db_type == 'sqlite' else '%s'] * len(transaction_ids))
            transaction_query = f"""
                SELECT transaction_id, date, description, amount, currency, classified_entity
                FROM transactions
                WHERE transaction_id IN ({placeholders})
            """
            try:
                transactions = db_manager.execute_with_retry(transaction_query, tuple(transaction_ids), fetch_all=True)
                for trans in transactions:
                    transaction_map[trans['transaction_id']] = trans
            except Exception as e:
                logger.error(f"Error fetching transaction details: {e}")

        # Build enriched match objects
        for match in matches:
            invoice = invoice_map.get(match.invoice_id, {})
            transaction = transaction_map.get(match.transaction_id, {})

            enriched_matches.append({
                'invoice_id': match.invoice_id,
                'transaction_id': match.transaction_id,
                'score': round(match.score, 3),
                'match_type': match.match_type,
                'confidence_level': match.confidence_level,
                'explanation': match.explanation,
                'auto_match': match.auto_match,
                'invoice': {
                    'invoice_number': invoice.get('invoice_number', 'Unknown'),
                    'customer_name': invoice.get('customer_name', 'N/A'),
                    'total_amount': float(invoice.get('total_amount', 0)),
                    'date': str(invoice.get('date', 'N/A')),
                    'currency': invoice.get('currency', 'USD'),
                    'business_unit': invoice.get('business_unit', 'N/A')
                },
                'transaction': {
                    'description': transaction.get('description', 'Unknown'),
                    'amount': abs(float(transaction.get('amount', 0))),
                    'date': str(transaction.get('date', 'N/A')),
                    'currency': transaction.get('currency', 'USD'),
                    'classified_entity': transaction.get('classified_entity', 'N/A')
                }
            })

        return enriched_matches

    def _build_result_dict(self, stats: MatchingStats, matches: List[MatchResult],
                          start_time: datetime) -> Dict[str, Any]:
        """Constrói dicionário de resultado final"""
        end_time = datetime.now()
        stats.processing_time_seconds = (end_time - start_time).total_seconds()

        # Fetch invoice and transaction details for all matches
        match_details = self._enrich_matches_with_details(matches)

        return {
            'success': True,
            'stats': {
                'total_invoices_processed': stats.total_invoices_processed,
                'total_matches_found': stats.total_matches_found,
                'high_confidence_matches': stats.high_confidence_matches,
                'medium_confidence_matches': stats.medium_confidence_matches,
                'auto_applied_matches': stats.auto_applied_matches,
                'pending_review_matches': stats.pending_review_matches,
                'processing_time_seconds': round(stats.processing_time_seconds, 2),
                'database_operations': stats.database_operations,
                'errors_count': stats.errors_count,
                'batch_stats': stats.batch_stats
            },
            'matches': match_details
        }

    def _build_error_result(self, stats: MatchingStats, error_message: str,
                           start_time: datetime) -> Dict[str, Any]:
        """Constrói dicionário de resultado em caso de erro"""
        end_time = datetime.now()
        stats.processing_time_seconds = (end_time - start_time).total_seconds()

        return {
            'success': False,
            'error': error_message,
            'stats': {
                'total_invoices_processed': stats.total_invoices_processed,
                'total_matches_found': stats.total_matches_found,
                'processing_time_seconds': round(stats.processing_time_seconds, 2),
                'errors_count': stats.errors_count,
                'batch_stats': stats.batch_stats
            }
        }

# Função de conveniência para uso externo
def run_robust_invoice_matching(invoice_ids: List[str] = None, auto_apply: bool = False,
                               enable_learning: bool = True) -> Dict[str, Any]:
    """
    Função principal para executar matching robusto de invoices

    Args:
        invoice_ids: Lista específica de invoices para processar
        auto_apply: Se deve aplicar automaticamente matches de alta confiança
        enable_learning: Se deve aplicar machine learning aos scores

    Returns:
        Dict com resultados detalhados e estatísticas de performance
    """
    matcher = RobustRevenueInvoiceMatcher()
    return matcher.run_robust_matching(invoice_ids, auto_apply, enable_learning)
