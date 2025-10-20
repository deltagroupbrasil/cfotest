#!/usr/bin/env python3
"""
Revenue Matcher - Sistema Inteligente de Matching de Invoices com Transações
Automatiza a identificação de invoices pagos através de análise de transações

Funcionalidades:
- Matching por valor (exato e aproximado)
- Matching por data (vencimento vs data transação)
- Matching por vendor/descrição (fuzzy matching)
- Matching semântico com Claude AI
- Sistema de pontuação e confiança
- Aprendizado de padrões
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

class RevenueInvoiceMatcher:
    """
    Motor principal de matching entre invoices e transações
    """

    def __init__(self):
        self.claude_client = self._init_claude_client()
        self.match_threshold_high = 0.90  # Match automático
        self.match_threshold_medium = 0.70  # Match sugerido
        self.amount_tolerance = 0.02  # 2% tolerance for amount matching

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

    def find_matches_for_invoices(self, invoice_ids: List[str] = None) -> List[MatchResult]:
        """
        Encontra matches para invoices específicos ou todos os não matchados

        Args:
            invoice_ids: Lista de IDs de invoices. Se None, processa todos não matchados

        Returns:
            Lista de MatchResult com os matches encontrados
        """
        logger.info(f"Starting invoice matching process...")

        # Buscar invoices não matchados
        invoices = self._get_unmatched_invoices(invoice_ids)
        if not invoices:
            logger.info("No unmatched invoices found")
            return []

        # Buscar transações candidatas (últimos 6 meses)
        transactions = self._get_candidate_transactions()
        if not transactions:
            logger.info("No candidate transactions found")
            return []

        logger.info(f"Processing {len(invoices)} invoices against {len(transactions)} transactions")

        matches = []
        for invoice in invoices:
            invoice_matches = self._find_matches_for_single_invoice(invoice, transactions)
            matches.extend(invoice_matches)

        # Ordenar por score descendente
        matches.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(matches)} potential matches")
        return matches

    def _get_unmatched_invoices(self, invoice_ids: List[str] = None) -> List[Dict]:
        """Busca invoices que ainda não foram matchados"""
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

        query += " ORDER BY date DESC"

        try:
            return db_manager.execute_query(query, tuple(params), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching unmatched invoices: {e}")
            return []

    def _get_candidate_transactions(self, days_back: int = 180) -> List[Dict]:
        """Busca transações candidatas para matching (últimos X dias)"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        query = """
            SELECT transaction_id, date, description, amount, currency,
                   classified_entity, origin, destination, source_file
            FROM transactions
            WHERE date >= ? AND amount > 0
            ORDER BY date DESC
        """

        # Adjust for PostgreSQL
        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            return db_manager.execute_query(query, (cutoff_date,), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching candidate transactions: {e}")
            return []

    def _find_matches_for_single_invoice(self, invoice: Dict, transactions: List[Dict]) -> List[MatchResult]:
        """Encontra matches para um único invoice"""
        matches = []

        for transaction in transactions:
            match_result = self._evaluate_match(invoice, transaction)
            if match_result and match_result.score >= self.match_threshold_medium:
                matches.append(match_result)

        return matches

    def _evaluate_match(self, invoice: Dict, transaction: Dict) -> Optional[MatchResult]:
        """Avalia se um invoice e transação são um match"""

        # Verificar critérios básicos
        criteria_scores = {}

        # 1. Matching por valor
        amount_score = self._calculate_amount_match_score(invoice, transaction)
        criteria_scores['amount'] = amount_score

        # 2. Matching por data
        date_score = self._calculate_date_match_score(invoice, transaction)
        criteria_scores['date'] = date_score

        # 3. Matching por vendor/descrição
        vendor_score = self._calculate_vendor_match_score(invoice, transaction)
        criteria_scores['vendor'] = vendor_score

        # 4. Matching por business unit/entity
        entity_score = self._calculate_entity_match_score(invoice, transaction)
        criteria_scores['entity'] = entity_score

        # 5. Pattern matching (invoice number, etc.)
        pattern_score = self._calculate_pattern_match_score(invoice, transaction)
        criteria_scores['pattern'] = pattern_score

        # Calcular score final ponderado
        final_score = (
            amount_score * 0.35 +      # Valor é muito importante
            date_score * 0.20 +        # Data é importante
            vendor_score * 0.25 +      # Vendor matching é crucial
            entity_score * 0.10 +      # Entity matching é útil
            pattern_score * 0.10       # Patterns são bônus
        )

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

    def _calculate_amount_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por valor"""
        try:
            invoice_amount = float(invoice['total_amount'])
            transaction_amount = float(transaction['amount'])

            # Exact match
            if abs(invoice_amount - transaction_amount) < 0.01:
                return 1.0

            # Percentage difference
            diff_percentage = abs(invoice_amount - transaction_amount) / invoice_amount

            if diff_percentage <= self.amount_tolerance:
                return 0.95  # Very close match
            elif diff_percentage <= 0.05:  # 5%
                return 0.80
            elif diff_percentage <= 0.10:  # 10%
                return 0.60
            elif diff_percentage <= 0.20:  # 20%
                return 0.30
            else:
                return 0.0

        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0

    def _calculate_date_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por data"""
        try:
            # Parse dates
            invoice_date = datetime.strptime(invoice['date'], '%Y-%m-%d')
            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')

            # Use due date if available, otherwise invoice date
            due_date = invoice.get('due_date')
            if due_date:
                target_date = datetime.strptime(due_date, '%Y-%m-%d')
            else:
                target_date = invoice_date

            # Calculate difference in days
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

        # Exact match
        if vendor_name in transaction_desc or transaction_desc in vendor_name:
            return 1.0

        # Fuzzy matching usando SequenceMatcher
        similarity = SequenceMatcher(None, vendor_name, transaction_desc).ratio()

        if similarity >= 0.8:
            return similarity
        elif similarity >= 0.6:
            return similarity * 0.8  # Penalize partial matches
        elif similarity >= 0.4:
            return similarity * 0.6
        else:
            # Try matching individual words
            vendor_words = set(vendor_name.split())
            desc_words = set(transaction_desc.split())

            if vendor_words & desc_words:  # Common words
                common_ratio = len(vendor_words & desc_words) / len(vendor_words)
                return min(common_ratio * 0.7, 0.6)

        return 0.0

    def _calculate_entity_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por business unit/entity"""
        invoice_entity = (invoice.get('business_unit') or '').lower().strip()
        transaction_entity = (transaction.get('classified_entity') or '').lower().strip()

        if not invoice_entity or not transaction_entity:
            return 0.5  # Neutral quando não tem info

        # Direct match
        if invoice_entity == transaction_entity:
            return 1.0

        # Partial matches
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

        # Look for invoice number in transaction description
        if invoice_number in transaction_desc:
            return 1.0

        # Look for numeric patterns
        invoice_numbers = re.findall(r'\d+', invoice_number)
        desc_numbers = re.findall(r'\d+', transaction_desc)

        for inv_num in invoice_numbers:
            if len(inv_num) >= 4 and inv_num in desc_numbers:  # Only significant numbers
                return 0.8

        return 0.0

    def _determine_match_type(self, criteria_scores: Dict[str, float]) -> str:
        """Determina o tipo principal de match baseado nos scores"""
        max_score = max(criteria_scores.values())
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
        """Gera explicação textual do porquê do match"""
        explanations = []

        if criteria_scores['amount'] >= 0.9:
            explanations.append(f"Valor exato/muito próximo ({invoice['total_amount']} ≈ {transaction['amount']})")
        elif criteria_scores['amount'] >= 0.7:
            explanations.append(f"Valor compatível ({invoice['total_amount']} ~ {transaction['amount']})")

        if criteria_scores['vendor'] >= 0.8:
            explanations.append(f"Vendor match: '{invoice.get('vendor_name', '')}' em '{transaction.get('description', '')}'")

        if criteria_scores['date'] >= 0.8:
            explanations.append(f"Data próxima ao vencimento ({invoice.get('due_date', invoice['date'])} ~ {transaction['date']})")

        if criteria_scores['pattern'] >= 0.8:
            explanations.append(f"Invoice# {invoice.get('invoice_number', '')} encontrado na descrição")

        if criteria_scores['entity'] >= 0.8:
            explanations.append(f"Mesmo business unit ({invoice.get('business_unit', '')})")

        return " | ".join(explanations) if explanations else "Match baseado em múltiplos critérios"

    def apply_semantic_matching(self, matches: List[MatchResult],
                              invoices: List[Dict], transactions: List[Dict]) -> List[MatchResult]:
        """
        Aplica matching semântico usando Claude AI para matches ambíguos
        """
        if not self.claude_client:
            logger.warning("Claude client not available - skipping semantic matching")
            return matches

        # Apenas para matches com score médio que podem se beneficiar de análise semântica
        ambiguous_matches = [m for m in matches if 0.7 <= m.score < 0.85]

        if not ambiguous_matches:
            return matches

        logger.info(f"Applying semantic matching to {len(ambiguous_matches)} ambiguous matches")

        enhanced_matches = []
        for match in ambiguous_matches:
            try:
                enhanced_match = self._enhance_match_with_ai(match, invoices, transactions)
                enhanced_matches.append(enhanced_match)
            except Exception as e:
                logger.error(f"Error in semantic matching for {match.invoice_id}: {e}")
                enhanced_matches.append(match)  # Keep original if AI fails

        # Replace ambiguous matches with enhanced ones
        final_matches = [m for m in matches if m not in ambiguous_matches]
        final_matches.extend(enhanced_matches)

        return final_matches

    def _enhance_match_with_ai(self, match: MatchResult,
                             invoices: List[Dict], transactions: List[Dict]) -> MatchResult:
        """Usa Claude AI para melhorar o matching de um par específico"""

        # Find the specific invoice and transaction
        invoice = next((i for i in invoices if i['id'] == match.invoice_id), None)
        transaction = next((t for t in transactions if t['transaction_id'] == match.transaction_id), None)

        if not invoice or not transaction:
            return match

        prompt = f"""
        Analise se esta transação bancária corresponde ao pagamento desta invoice:

        INVOICE:
        - Número: {invoice.get('invoice_number', 'N/A')}
        - Vendor: {invoice.get('vendor_name', 'N/A')}
        - Valor: {invoice.get('currency', 'USD')} {invoice.get('total_amount', 0)}
        - Data: {invoice.get('date', 'N/A')}
        - Vencimento: {invoice.get('due_date', 'N/A')}
        - Business Unit: {invoice.get('business_unit', 'N/A')}

        TRANSAÇÃO:
        - Descrição: {transaction.get('description', 'N/A')}
        - Valor: {transaction.get('currency', 'USD')} {transaction.get('amount', 0)}
        - Data: {transaction.get('date', 'N/A')}
        - Entity: {transaction.get('classified_entity', 'N/A')}
        - Origem: {transaction.get('origin', 'N/A')}
        - Destino: {transaction.get('destination', 'N/A')}

        Score atual: {match.score:.2f}

        Considere:
        1. Variações de nome do vendor (siglas, nomes completos, etc.)
        2. Diferenças menores de valor (taxas, ajustes, etc.)
        3. Padrões típicos de pagamento
        4. Contexto do business unit

        Responda em JSON:
        {{
            "is_match": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "explicação detalhada",
            "adjusted_score": 0.0-1.0
        }}
        """

        try:
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Usar modelo mais barato para esta tarefa
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)

            # Update match based on AI analysis
            if result.get('is_match', False) and result.get('confidence', 0) > 0.7:
                adjusted_score = min(result.get('adjusted_score', match.score), 0.95)
                enhanced_explanation = f"{match.explanation} | AI: {result.get('reasoning', '')}"

                return MatchResult(
                    invoice_id=match.invoice_id,
                    transaction_id=match.transaction_id,
                    score=adjusted_score,
                    match_type=f"{match.match_type}_AI_ENHANCED",
                    criteria_scores=match.criteria_scores,
                    confidence_level="HIGH" if adjusted_score >= 0.9 else "MEDIUM",
                    explanation=enhanced_explanation,
                    auto_match=adjusted_score >= 0.9
                )
            else:
                # AI says it's not a match or low confidence
                return MatchResult(
                    invoice_id=match.invoice_id,
                    transaction_id=match.transaction_id,
                    score=max(match.score * 0.7, 0.3),  # Reduce score
                    match_type=f"{match.match_type}_AI_REJECTED",
                    criteria_scores=match.criteria_scores,
                    confidence_level="LOW",
                    explanation=f"{match.explanation} | AI: {result.get('reasoning', '')}",
                    auto_match=False
                )

        except Exception as e:
            logger.error(f"Error in Claude API call: {e}")
            return match

    def save_match_results(self, matches: List[MatchResult], auto_apply: bool = False) -> Dict[str, int]:
        """
        Salva resultados de matching no banco de dados

        Args:
            matches: Lista de matches encontrados
            auto_apply: Se True, aplica automaticamente matches com high confidence

        Returns:
            Dict com estatísticas de quantos matches foram aplicados, salvos para revisão, etc.
        """
        stats = {
            'auto_applied': 0,
            'pending_review': 0,
            'total_processed': 0
        }

        for match in matches:
            try:
                if auto_apply and match.auto_match:
                    # Apply match automatically
                    self._apply_match(match)
                    stats['auto_applied'] += 1
                else:
                    # Save for manual review
                    self._save_pending_match(match)
                    stats['pending_review'] += 1

                stats['total_processed'] += 1

            except Exception as e:
                logger.error(f"Error saving match {match.invoice_id}-{match.transaction_id}: {e}")

        logger.info(f"Processed {stats['total_processed']} matches: "
                   f"{stats['auto_applied']} auto-applied, {stats['pending_review']} pending review")

        return stats

    def _apply_match(self, match: MatchResult):
        """Aplica um match automaticamente"""
        query = """
            UPDATE invoices
            SET linked_transaction_id = ?,
                status = 'paid',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        db_manager.execute_query(query, (match.transaction_id, match.invoice_id))

        # Log the automatic match
        self._log_match_action(match, 'AUTO_APPLIED', 'System')

    def _save_pending_match(self, match: MatchResult):
        """Salva match para revisão manual"""
        # Create pending matches table if not exists
        self._ensure_pending_matches_table()

        query = """
            INSERT INTO pending_invoice_matches
            (invoice_id, transaction_id, score, match_type, criteria_scores,
             confidence_level, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        db_manager.execute_query(query, (
            match.invoice_id,
            match.transaction_id,
            match.score,
            match.match_type,
            json.dumps(match.criteria_scores),
            match.confidence_level,
            match.explanation
        ))

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

    def _log_match_action(self, match: MatchResult, action: str, user: str):
        """Registra ações de matching para auditoria"""
        # Create log table if not exists
        self._ensure_match_log_table()

        query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            db_manager.execute_query(query, (
                match.invoice_id,
                match.transaction_id,
                action,
                match.score,
                match.match_type,
                user
            ))
        except Exception as e:
            logger.error(f"Error logging match action: {e}")

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

# Convenience function for external use
def run_invoice_matching(invoice_ids: List[str] = None, auto_apply: bool = False) -> Dict[str, Any]:
    """
    Função principal para executar matching de invoices

    Args:
        invoice_ids: Lista específica de invoices para processar
        auto_apply: Se deve aplicar automaticamente matches de alta confiança

    Returns:
        Dict com resultados e estatísticas
    """
    matcher = RevenueInvoiceMatcher()

    # Find matches
    matches = matcher.find_matches_for_invoices(invoice_ids)

    # Apply semantic matching to improve ambiguous cases
    if matches:
        # Get full data for semantic matching
        invoices = matcher._get_unmatched_invoices(invoice_ids)
        transactions = matcher._get_candidate_transactions()
        matches = matcher.apply_semantic_matching(matches, invoices, transactions)

    # Save results
    stats = matcher.save_match_results(matches, auto_apply)

    return {
        'success': True,
        'total_matches': len(matches),
        'high_confidence': len([m for m in matches if m.confidence_level == 'HIGH']),
        'medium_confidence': len([m for m in matches if m.confidence_level == 'MEDIUM']),
        'auto_applied': stats['auto_applied'],
        'pending_review': stats['pending_review'],
        'matches': [
            {
                'invoice_id': m.invoice_id,
                'transaction_id': m.transaction_id,
                'score': m.score,
                'match_type': m.match_type,
                'confidence_level': m.confidence_level,
                'explanation': m.explanation,
                'auto_match': m.auto_match
            }
            for m in matches
        ]
    }
