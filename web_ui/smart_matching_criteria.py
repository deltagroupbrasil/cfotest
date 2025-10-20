#!/usr/bin/env python3
"""
Smart Matching Criteria - Critérios Inteligentes para Revenue Matching
Sistema melhorado com validação rigorosa e descrições claras da IA

Corrige problemas como:
- USD 6.660,35 vs $3.002,40 (diferença de >50% rejeitada)
- Matches suspeitos com baixa correlação
- Falta de contexto nas explicações
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MatchCriteria:
    """Critérios detalhados de matching com descrições da IA"""
    amount_score: float
    amount_explanation: str
    date_score: float
    date_explanation: str
    vendor_score: float
    vendor_explanation: str
    entity_score: float
    entity_explanation: str
    pattern_score: float
    pattern_explanation: str
    sanity_check_passed: bool
    sanity_warnings: List[str]
    overall_explanation: str
    ai_confidence: str
    recommendation: str

class SmartMatchingValidator:
    """
    Validador inteligente para critérios de matching
    Implementa regras rigorosas e descrições claras
    """

    def __init__(self):
        self.claude_client = self._init_claude_client()

        # Critérios MUITO mais rigorosos
        self.amount_tolerance_strict = 0.02  # 2% máximo
        self.amount_tolerance_loose = 0.05   # 5% máximo para casos especiais
        self.amount_max_difference = 0.15    # 15% diferença máxima absoluta

        # Thresholds revisados
        self.match_threshold_high = 0.85     # Mais rigoroso (era 0.90)
        self.match_threshold_medium = 0.70   # Mantido
        self.match_threshold_minimum = 0.50  # Mínimo para considerar

    def _init_claude_client(self):
        """Inicializa cliente Claude para descrições inteligentes"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                return anthropic.Anthropic(api_key=api_key.strip())
            else:
                logger.warning("Claude API key not found - AI descriptions disabled")
                return None
        except Exception as e:
            logger.error(f"Error initializing Claude: {e}")
            return None

    def evaluate_smart_match(self, invoice: Dict, transaction: Dict) -> MatchCriteria:
        """
        Avalia match com critérios inteligentes e validação rigorosa

        Args:
            invoice: Dados do invoice
            transaction: Dados da transação

        Returns:
            MatchCriteria com scores detalhados e explicações da IA
        """

        # 1. Calcular critérios individuais
        amount_score, amount_explanation = self._calculate_smart_amount_score(invoice, transaction)
        date_score, date_explanation = self._calculate_smart_date_score(invoice, transaction)
        vendor_score, vendor_explanation = self._calculate_smart_vendor_score(invoice, transaction)
        entity_score, entity_explanation = self._calculate_smart_entity_score(invoice, transaction)
        pattern_score, pattern_explanation = self._calculate_smart_pattern_score(invoice, transaction)

        # 2. Validação de sanidade rigorosa
        sanity_check_passed, sanity_warnings = self._perform_sanity_checks(
            invoice, transaction, amount_score, date_score, vendor_score
        )

        # 3. Gerar explicação geral inteligente
        overall_explanation = self._generate_overall_explanation(
            invoice, transaction, amount_score, date_score, vendor_score,
            entity_score, pattern_score, sanity_warnings
        )

        # 4. Determinar confiança da IA
        ai_confidence = self._determine_ai_confidence(
            amount_score, date_score, vendor_score, entity_score, pattern_score,
            sanity_check_passed
        )

        # 5. Gerar recomendação
        recommendation = self._generate_recommendation(
            amount_score, date_score, vendor_score, sanity_check_passed, ai_confidence
        )

        return MatchCriteria(
            amount_score=amount_score,
            amount_explanation=amount_explanation,
            date_score=date_score,
            date_explanation=date_explanation,
            vendor_score=vendor_score,
            vendor_explanation=vendor_explanation,
            entity_score=entity_score,
            entity_explanation=entity_explanation,
            pattern_score=pattern_score,
            pattern_explanation=pattern_explanation,
            sanity_check_passed=sanity_check_passed,
            sanity_warnings=sanity_warnings,
            overall_explanation=overall_explanation,
            ai_confidence=ai_confidence,
            recommendation=recommendation
        )

    def _calculate_smart_amount_score(self, invoice: Dict, transaction: Dict) -> Tuple[float, str]:
        """Calcula score de valor com critérios muito mais rigorosos"""
        try:
            invoice_amount = float(invoice['total_amount'])
            transaction_amount = float(transaction['amount'])

            # Validação básica
            if invoice_amount <= 0 or transaction_amount <= 0:
                return 0.0, "❌ Valores inválidos (zero ou negativos)"

            # Diferença absoluta e percentual
            absolute_diff = abs(invoice_amount - transaction_amount)
            percentage_diff = absolute_diff / invoice_amount

            # Critérios MUITO mais rigorosos
            if absolute_diff < 0.01:  # Praticamente igual
                explanation = f"✅ Valores praticamente idênticos: {invoice['currency']} {invoice_amount:,.2f} ≈ ${transaction_amount:,.2f} (diferença: {absolute_diff:.2f})"
                return 1.0, explanation

            elif percentage_diff <= self.amount_tolerance_strict:  # 2%
                explanation = f"✅ Valores muito próximos: {invoice['currency']} {invoice_amount:,.2f} ~ ${transaction_amount:,.2f} (diferença: {percentage_diff:.1%})"
                return 0.90, explanation

            elif percentage_diff <= self.amount_tolerance_loose:  # 5%
                explanation = f"⚠️ Valores próximos mas com diferença significativa: {invoice['currency']} {invoice_amount:,.2f} ~ ${transaction_amount:,.2f} (diferença: {percentage_diff:.1%})"
                return 0.75, explanation

            elif percentage_diff <= 0.10:  # 10%
                explanation = f"⚠️ Diferença considerável: {invoice['currency']} {invoice_amount:,.2f} vs ${transaction_amount:,.2f} (diferença: {percentage_diff:.1%})"
                return 0.50, explanation

            elif percentage_diff <= self.amount_max_difference:  # 15%
                explanation = f"❌ Diferença muito alta: {invoice['currency']} {invoice_amount:,.2f} vs ${transaction_amount:,.2f} (diferença: {percentage_diff:.1%})"
                return 0.20, explanation

            else:  # >15%
                explanation = f"❌ Valores incompatíveis: {invoice['currency']} {invoice_amount:,.2f} vs ${transaction_amount:,.2f} (diferença: {percentage_diff:.1%} - muito alta)"
                return 0.0, explanation

        except (ValueError, TypeError, ZeroDivisionError) as e:
            return 0.0, f"❌ Erro no cálculo de valores: {str(e)}"

    def _calculate_smart_date_score(self, invoice: Dict, transaction: Dict) -> Tuple[float, str]:
        """Calcula score de data com explicações detalhadas"""
        try:
            invoice_date = datetime.strptime(invoice['date'], '%Y-%m-%d')
            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')

            # Data de vencimento como referência preferencial
            due_date = invoice.get('due_date')
            if due_date:
                reference_date = datetime.strptime(due_date, '%Y-%m-%d')
                date_context = f"vencimento {due_date}"
            else:
                reference_date = invoice_date
                date_context = f"emissão {invoice['date']}"

            diff_days = abs((transaction_date - reference_date).days)

            if diff_days == 0:
                explanation = f"✅ Data exata: Transação em {transaction['date']} = data de {date_context}"
                return 1.0, explanation
            elif diff_days <= 1:
                explanation = f"✅ Data quase exata: Transação em {transaction['date']}, 1 dia de diferença da {date_context}"
                return 0.95, explanation
            elif diff_days <= 3:
                explanation = f"✅ Data muito próxima: Transação em {transaction['date']}, {diff_days} dias da {date_context}"
                return 0.85, explanation
            elif diff_days <= 7:
                explanation = f"⚠️ Data próxima: Transação em {transaction['date']}, {diff_days} dias da {date_context}"
                return 0.70, explanation
            elif diff_days <= 15:
                explanation = f"⚠️ Data com diferença moderada: Transação em {transaction['date']}, {diff_days} dias da {date_context}"
                return 0.50, explanation
            elif diff_days <= 30:
                explanation = f"⚠️ Data com diferença considerável: Transação em {transaction['date']}, {diff_days} dias da {date_context}"
                return 0.30, explanation
            elif diff_days <= 60:
                explanation = f"❌ Data com diferença alta: Transação em {transaction['date']}, {diff_days} dias da {date_context}"
                return 0.15, explanation
            else:
                explanation = f"❌ Datas incompatíveis: Transação em {transaction['date']}, {diff_days} dias da {date_context} (muito distante)"
                return 0.0, explanation

        except (ValueError, TypeError) as e:
            return 0.0, f"❌ Erro no processamento de datas: {str(e)}"

    def _calculate_smart_vendor_score(self, invoice: Dict, transaction: Dict) -> Tuple[float, str]:
        """Calcula score de vendor com análise inteligente"""
        vendor_name = (invoice.get('vendor_name') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not vendor_name or not transaction_desc:
            return 0.0, "❌ Informações de vendor/descrição ausentes"

        # Análise de correspondência exata
        if vendor_name == transaction_desc:
            return 1.0, f"✅ Correspondência exata: '{vendor_name}' = '{transaction_desc}'"

        # Análise de inclusão
        if vendor_name in transaction_desc:
            return 0.90, f"✅ Vendor encontrado na descrição: '{vendor_name}' em '{transaction_desc}'"

        if transaction_desc in vendor_name:
            return 0.85, f"✅ Descrição encontrada no vendor: '{transaction_desc}' em '{vendor_name}'"

        # Análise de similaridade
        similarity = SequenceMatcher(None, vendor_name, transaction_desc).ratio()

        if similarity >= 0.8:
            return similarity, f"✅ Alta similaridade ({similarity:.1%}): '{vendor_name}' ~ '{transaction_desc}'"
        elif similarity >= 0.6:
            return similarity * 0.8, f"⚠️ Similaridade moderada ({similarity:.1%}): '{vendor_name}' ~ '{transaction_desc}'"
        elif similarity >= 0.4:
            return similarity * 0.6, f"⚠️ Similaridade baixa ({similarity:.1%}): '{vendor_name}' ~ '{transaction_desc}'"

        # Análise de palavras comuns
        vendor_words = set(vendor_name.split())
        desc_words = set(transaction_desc.split())
        common_words = vendor_words & desc_words

        if common_words:
            common_ratio = len(common_words) / len(vendor_words)
            significant_words = [w for w in common_words if len(w) > 3]  # Palavras significativas

            if significant_words:
                explanation = f"⚠️ Palavras comuns significativas: {', '.join(significant_words)} ({common_ratio:.1%} de correspondência)"
                return min(common_ratio * 0.7, 0.6), explanation
            else:
                explanation = f"⚠️ Apenas palavras pequenas em comum: {', '.join(common_words)}"
                return min(common_ratio * 0.4, 0.3), explanation

        return 0.0, f"❌ Nenhuma correspondência encontrada entre '{vendor_name}' e '{transaction_desc}'"

    def _calculate_smart_entity_score(self, invoice: Dict, transaction: Dict) -> Tuple[float, str]:
        """Calcula score de business entity com mapeamento inteligente"""
        invoice_entity = (invoice.get('business_unit') or '').lower().strip()
        transaction_entity = (transaction.get('classified_entity') or '').lower().strip()

        if not invoice_entity and not transaction_entity:
            return 0.5, "⚠️ Informações de business unit ausentes em ambos"

        if not invoice_entity:
            return 0.3, f"⚠️ Business unit ausente no invoice (transação: '{transaction_entity}')"

        if not transaction_entity:
            return 0.3, f"⚠️ Entity ausente na transação (invoice: '{invoice_entity}')"

        # Correspondência exata
        if invoice_entity == transaction_entity:
            return 1.0, f"✅ Business units idênticas: '{invoice_entity}'"

        # Mapeamento inteligente de entidades
        entity_mapping = {
            'delta mining': ['delta mining', 'delta', 'mining', 'delta mining paraguay'],
            'delta llc': ['delta llc', 'delta', 'llc'],
            'delta prop': ['delta prop', 'prop shop', 'prop', 'delta proprietary'],
            'delta brazil': ['delta brazil', 'brazil', 'brasil'],
            'pegasus': ['pegasus', 'pegasus technologies', 'pegasus tech'],
            'paraguay': ['paraguay', 'py', 'delta mining paraguay']
        }

        # Verificar mapeamentos
        for main_entity, variants in entity_mapping.items():
            invoice_in_group = any(variant in invoice_entity for variant in variants)
            transaction_in_group = any(variant in transaction_entity for variant in variants)

            if invoice_in_group and transaction_in_group:
                return 0.8, f"✅ Entities relacionadas no grupo '{main_entity}': '{invoice_entity}' ~ '{transaction_entity}'"

        # Análise de palavras comuns
        invoice_words = set(invoice_entity.split())
        transaction_words = set(transaction_entity.split())
        common_words = invoice_words & transaction_words

        if common_words:
            common_ratio = len(common_words) / max(len(invoice_words), len(transaction_words))
            return min(common_ratio * 0.6, 0.5), f"⚠️ Palavras comuns: {', '.join(common_words)} ('{invoice_entity}' ~ '{transaction_entity}')"

        return 0.1, f"❌ Business units incompatíveis: '{invoice_entity}' vs '{transaction_entity}'"

    def _calculate_smart_pattern_score(self, invoice: Dict, transaction: Dict) -> Tuple[float, str]:
        """Calcula score de padrões (invoice numbers, etc.) com análise inteligente"""
        invoice_number = (invoice.get('invoice_number') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not invoice_number or not transaction_desc:
            return 0.0, "⚠️ Número do invoice ou descrição ausentes"

        # Correspondência exata do número do invoice
        if invoice_number in transaction_desc:
            return 1.0, f"✅ Número do invoice encontrado: '{invoice_number}' em '{transaction_desc}'"

        # Extrair números significativos
        invoice_numbers = re.findall(r'\d{3,}', invoice_number)  # Números com 3+ dígitos
        desc_numbers = re.findall(r'\d{3,}', transaction_desc)

        # Verificar correspondências numéricas
        for inv_num in invoice_numbers:
            if inv_num in desc_numbers:
                if len(inv_num) >= 6:  # Números longos são mais específicos
                    return 0.9, f"✅ Número específico encontrado: '{inv_num}' (de '{invoice_number}') em '{transaction_desc}'"
                elif len(inv_num) >= 4:
                    return 0.7, f"⚠️ Número moderadamente específico: '{inv_num}' (de '{invoice_number}') em '{transaction_desc}'"
                else:
                    return 0.4, f"⚠️ Número pouco específico: '{inv_num}' (de '{invoice_number}') em '{transaction_desc}'"

        # Verificar padrões de data no invoice number
        date_patterns = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{8}|\d{6}', invoice_number)
        if date_patterns:
            for pattern in date_patterns:
                if pattern in transaction_desc:
                    return 0.6, f"⚠️ Padrão de data encontrado: '{pattern}' (de '{invoice_number}') em '{transaction_desc}'"

        return 0.0, f"❌ Nenhum padrão identificado entre '{invoice_number}' e '{transaction_desc}'"

    def _perform_sanity_checks(self, invoice: Dict, transaction: Dict,
                              amount_score: float, date_score: float, vendor_score: float) -> Tuple[bool, List[str]]:
        """Realiza verificações de sanidade rigorosas"""
        warnings = []
        critical_issues = []

        # 1. Verificação de diferença de valor extrema
        try:
            invoice_amount = float(invoice['total_amount'])
            transaction_amount = float(transaction['amount'])
            percentage_diff = abs(invoice_amount - transaction_amount) / invoice_amount

            if percentage_diff > 0.50:  # >50% de diferença
                critical_issues.append(f"Diferença de valor extrema: {percentage_diff:.1%}")
            elif percentage_diff > 0.25:  # >25% de diferença
                warnings.append(f"Diferença de valor alta: {percentage_diff:.1%}")

        except (ValueError, TypeError):
            critical_issues.append("Valores inválidos ou ausentes")

        # 2. Verificação de datas muito distantes
        try:
            invoice_date = datetime.strptime(invoice['date'], '%Y-%m-%d')
            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
            diff_days = abs((transaction_date - invoice_date).days)

            if diff_days > 365:  # >1 ano
                critical_issues.append(f"Datas muito distantes: {diff_days} dias")
            elif diff_days > 90:  # >3 meses
                warnings.append(f"Datas distantes: {diff_days} dias")

        except (ValueError, TypeError):
            critical_issues.append("Datas inválidas")

        # 3. Verificação de scores muito baixos
        if amount_score < 0.3 and vendor_score < 0.3:
            critical_issues.append("Valores e vendors não correspondem")

        if amount_score < 0.5 and date_score < 0.3:
            warnings.append("Valores e datas com baixa correspondência")

        # 4. Verificação de moedas diferentes
        invoice_currency = invoice.get('currency', 'USD').upper()
        transaction_currency = 'USD'  # Assumindo que transações são sempre em USD

        if invoice_currency != transaction_currency:
            warnings.append(f"Moedas diferentes: Invoice {invoice_currency} vs Transação {transaction_currency}")

        # 5. Verificação de valores suspeitos
        try:
            invoice_amount = float(invoice['total_amount'])
            transaction_amount = float(transaction['amount'])

            # Valores muito baixos ou muito altos podem ser suspeitos
            if invoice_amount < 1 or transaction_amount < 1:
                warnings.append("Valores muito baixos (< $1)")
            elif invoice_amount > 1000000 or transaction_amount > 1000000:
                warnings.append("Valores muito altos (> $1M)")

        except (ValueError, TypeError):
            pass

        # Determinar se passou na verificação
        sanity_passed = len(critical_issues) == 0
        all_warnings = warnings + [f"CRÍTICO: {issue}" for issue in critical_issues]

        return sanity_passed, all_warnings

    def _generate_overall_explanation(self, invoice: Dict, transaction: Dict,
                                    amount_score: float, date_score: float, vendor_score: float,
                                    entity_score: float, pattern_score: float, warnings: List[str]) -> str:
        """Gera explicação geral inteligente do matching"""

        # Identificar critério dominante
        scores = {
            'Valor': amount_score,
            'Data': date_score,
            'Vendor': vendor_score,
            'Entity': entity_score,
            'Padrão': pattern_score
        }

        best_criterion = max(scores, key=scores.get)
        best_score = scores[best_criterion]

        # Calcular score geral ponderado
        overall_score = (
            amount_score * 0.40 +      # Peso maior para valor
            vendor_score * 0.30 +      # Vendor é muito importante
            date_score * 0.20 +        # Data moderadamente importante
            entity_score * 0.05 +      # Entity peso menor
            pattern_score * 0.05       # Pattern peso menor
        )

        # Gerar explicação baseada no score geral
        if overall_score >= 0.85:
            confidence_text = "ALTA CONFIANÇA"
            emoji = "✅"
        elif overall_score >= 0.70:
            confidence_text = "CONFIANÇA MODERADA"
            emoji = "⚠️"
        elif overall_score >= 0.50:
            confidence_text = "BAIXA CONFIANÇA"
            emoji = "❌"
        else:
            confidence_text = "MUITO BAIXA CONFIANÇA"
            emoji = "🚫"

        explanation = f"{emoji} {confidence_text} ({overall_score:.1%}): "
        explanation += f"Melhor critério: {best_criterion} ({best_score:.1%}). "

        # Adicionar detalhes dos principais critérios
        if amount_score >= 0.7:
            explanation += f"Valores compatíveis ({amount_score:.1%}). "
        elif amount_score < 0.3:
            explanation += f"Valores incompatíveis ({amount_score:.1%}). "

        if vendor_score >= 0.7:
            explanation += f"Vendor/descrição corresponde ({vendor_score:.1%}). "
        elif vendor_score < 0.3:
            explanation += f"Vendor/descrição não corresponde ({vendor_score:.1%}). "

        # Adicionar warnings se existirem
        if warnings:
            explanation += f"ATENÇÃO: {'; '.join(warnings[:2])}"  # Limitar a 2 warnings

        return explanation

    def _determine_ai_confidence(self, amount_score: float, date_score: float, vendor_score: float,
                                entity_score: float, pattern_score: float, sanity_passed: bool) -> str:
        """Determina confiança da IA no matching"""

        if not sanity_passed:
            return "REJEITADO - Falhou na verificação de sanidade"

        # Score ponderado
        weighted_score = (
            amount_score * 0.40 +
            vendor_score * 0.30 +
            date_score * 0.20 +
            entity_score * 0.05 +
            pattern_score * 0.05
        )

        # Verificações especiais
        if amount_score >= 0.9 and vendor_score >= 0.8:
            return "MUITO ALTA - Valor e vendor perfeitos"
        elif amount_score >= 0.8 and (vendor_score >= 0.7 or pattern_score >= 0.8):
            return "ALTA - Valor excelente com vendor ou padrão"
        elif weighted_score >= 0.75:
            return "ALTA - Múltiplos critérios fortes"
        elif weighted_score >= 0.60:
            return "MODERADA - Critérios razoáveis"
        elif weighted_score >= 0.45:
            return "BAIXA - Poucos critérios atendem"
        else:
            return "MUITO BAIXA - Critérios insuficientes"

    def _generate_recommendation(self, amount_score: float, date_score: float, vendor_score: float,
                               sanity_passed: bool, ai_confidence: str) -> str:
        """Gera recomendação de ação"""

        if not sanity_passed:
            return "REJEITAR - Não passou na verificação de sanidade"

        if "MUITO ALTA" in ai_confidence or "ALTA" in ai_confidence:
            if amount_score >= 0.85 and vendor_score >= 0.70:
                return "APROVAÇÃO AUTOMÁTICA - Alta confiança em valor e vendor"
            else:
                return "REVISÃO HUMANA RECOMENDADA - Alta confiança mas verificar detalhes"

        elif "MODERADA" in ai_confidence:
            return "REVISÃO HUMANA OBRIGATÓRIA - Confiança moderada"

        else:
            return "REJEITAR - Confiança insuficiente para matching"


def validate_invoice_transaction_match(invoice: Dict, transaction: Dict) -> MatchCriteria:
    """
    Função principal para validar match entre invoice e transação

    Args:
        invoice: Dados do invoice
        transaction: Dados da transação

    Returns:
        MatchCriteria com análise completa e recomendação
    """
    validator = SmartMatchingValidator()
    return validator.evaluate_smart_match(invoice, transaction)


def get_matching_criteria_explanation() -> str:
    """
    Retorna explicação completa dos critérios de matching
    """
    return """
    🔍 CRITÉRIOS INTELIGENTES DE REVENUE MATCHING

    📊 CRITÉRIO DE VALOR (Peso: 40%):
    • ✅ Idêntico (diferença < $0.01): Score 100%
    • ✅ Muito próximo (≤2%): Score 90%
    • ⚠️ Próximo (≤5%): Score 75%
    • ⚠️ Moderado (≤10%): Score 50%
    • ❌ Alto (≤15%): Score 20%
    • 🚫 Incompatível (>15%): Score 0%

    📅 CRITÉRIO DE DATA (Peso: 20%):
    • ✅ Data exata: Score 100%
    • ✅ 1 dia: Score 95%
    • ✅ 2-3 dias: Score 85%
    • ⚠️ 4-7 dias: Score 70%
    • ⚠️ 8-15 dias: Score 50%
    • ❌ 16-30 dias: Score 30%
    • 🚫 >30 dias: Score 0-15%

    🏢 CRITÉRIO DE VENDOR (Peso: 30%):
    • ✅ Correspondência exata: Score 100%
    • ✅ Nome incluído: Score 90%
    • ✅ Alta similaridade (>80%): Score 80%+
    • ⚠️ Similaridade moderada: Score 60%
    • ❌ Palavras comuns apenas: Score 30%
    • 🚫 Nenhuma correspondência: Score 0%

    🔢 CRITÉRIO DE PADRÃO (Peso: 5%):
    • ✅ Invoice number exato: Score 100%
    • ✅ Número específico (6+ dígitos): Score 90%
    • ⚠️ Número moderado (4-5 dígitos): Score 70%
    • ⚠️ Padrão de data: Score 60%
    • 🚫 Nenhum padrão: Score 0%

    🏛️ CRITÉRIO DE ENTITY (Peso: 5%):
    • ✅ Entities idênticas: Score 100%
    • ✅ Entities relacionadas: Score 80%
    • ⚠️ Palavras comuns: Score 30-50%
    • 🚫 Incompatíveis: Score 10%

    🛡️ VERIFICAÇÕES DE SANIDADE:
    • 🚫 Diferença de valor >50%: REJEIÇÃO
    • ⚠️ Diferença de valor >25%: WARNING
    • 🚫 Datas >1 ano: REJEIÇÃO
    • ⚠️ Datas >3 meses: WARNING
    • ⚠️ Moedas diferentes: WARNING

    🎯 RECOMENDAÇÕES FINAIS:
    • Score ≥85% + sanidade OK: APROVAÇÃO AUTOMÁTICA
    • Score 70-84%: REVISÃO HUMANA RECOMENDADA
    • Score 50-69%: REVISÃO HUMANA OBRIGATÓRIA
    • Score <50% ou falha sanidade: REJEIÇÃO
    """