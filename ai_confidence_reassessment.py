"""
AI Confidence Reassessment System
Dynamically reassesses transaction classifications using Claude AI with business context
"""

import anthropic
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Tuple


class AIConfidenceReassessor:
    """
    Reassesses transaction confidence scores using Claude AI with accumulated business context.
    Learns from user feedback and provides intelligent suggestions for improvements.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def should_reassess(self, transaction: Dict, db_conn) -> bool:
        """
        Determine if a transaction needs AI reassessment.

        Criteria:
        - Confidence < 0.7 (low/medium confidence)
        - Has not been reviewed in last 7 days
        - User has not manually confirmed it (user_feedback_count == 0)
        """
        confidence = float(transaction.get('confidence', 0))
        last_review = transaction.get('last_ai_review')
        user_feedback_count = transaction.get('user_feedback_count', 0)

        # Don't reassess if user has already confirmed
        if user_feedback_count > 0:
            return False

        # Don't reassess if high confidence
        if confidence >= 0.8:
            return False

        # Check if reviewed recently
        if last_review:
            if isinstance(last_review, str):
                from dateutil import parser
                last_review = parser.parse(last_review)
            if datetime.now() - last_review < timedelta(days=7):
                return False

        return True

    def get_similar_transactions(self, transaction: Dict, db_conn, limit: int = 10) -> List[Dict]:
        """
        Find similar transactions that user has edited/confirmed.
        Uses description similarity and amount ranges.
        """
        cursor = db_conn.cursor()

        description = transaction.get('description', '')
        amount = float(transaction.get('amount', 0))

        # Extract key words from description for similarity matching
        keywords = [word.upper() for word in description.split() if len(word) > 3][:5]

        # Build SQL query to find similar confirmed transactions
        if keywords:
            keyword_conditions = ' OR '.join([f"UPPER(description) LIKE '%{kw}%'" for kw in keywords])
            query = f"""
                SELECT transaction_id, date, description, amount, classified_entity,
                       accounting_category, justification, confidence, user_feedback_count
                FROM transactions
                WHERE user_feedback_count > 0
                AND ({keyword_conditions})
                AND ABS(amount - {amount}) < {abs(amount) * 0.5 + 100}
                ORDER BY user_feedback_count DESC, confidence DESC
                LIMIT {limit}
            """
        else:
            # Fallback: find by amount range only
            query = f"""
                SELECT transaction_id, date, description, amount, classified_entity,
                       accounting_category, justification, confidence, user_feedback_count
                FROM transactions
                WHERE user_feedback_count > 0
                AND ABS(amount - {amount}) < {abs(amount) * 0.5 + 100}
                ORDER BY user_feedback_count DESC, confidence DESC
                LIMIT {limit}
            """

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        similar = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return similar

    def get_learned_patterns(self, db_conn, limit: int = 20) -> List[Dict]:
        """Get most successful learned patterns from classification_patterns table"""
        cursor = db_conn.cursor()
        query = """
            SELECT description_pattern, entity, accounting_category,
                   confidence_score, usage_count, success_count
            FROM classification_patterns
            WHERE success_count > 0
            ORDER BY confidence_score DESC, usage_count DESC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        columns = [desc[0] for desc in cursor.description]
        patterns = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return patterns

    def reassess_with_context(
        self,
        transaction: Dict,
        similar_transactions: List[Dict],
        learned_patterns: List[Dict],
        business_knowledge: str
    ) -> Dict:
        """
        Use Claude AI to reassess transaction with full business context.

        Returns:
        {
            "confidence": float,  # New confidence score 0.0-1.0
            "suggestions": [
                {
                    "field": "classified_entity" | "accounting_category" | "justification",
                    "current_value": str,
                    "suggested_value": str,
                    "reasoning": str,
                    "confidence": float
                }
            ],
            "reasoning": str,  # Overall reasoning for confidence adjustment
            "should_review": bool  # Whether human review is recommended
        }
        """

        # Build comprehensive prompt
        prompt = self._build_reassessment_prompt(
            transaction, similar_transactions, learned_patterns, business_knowledge
        )

        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.2,  # Lower temperature for more consistent analysis
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = message.content[0].text
            result = self._parse_ai_response(response_text, transaction)

            return result

        except Exception as e:
            # Fallback if AI call fails
            return {
                "confidence": float(transaction.get('confidence', 0.5)),
                "suggestions": [],
                "reasoning": f"AI reassessment failed: {str(e)}",
                "should_review": True,
                "error": str(e)
            }

    def _build_reassessment_prompt(
        self,
        transaction: Dict,
        similar_transactions: List[Dict],
        learned_patterns: List[Dict],
        business_knowledge: str
    ) -> str:
        """Build detailed prompt for Claude AI"""

        prompt = f"""You are a financial transaction classification expert. Analyze the following transaction and provide suggestions for improving its classification.

TRANSACTION TO ANALYZE:
- Date: {transaction.get('date', 'N/A')}
- Description: {transaction.get('description', 'N/A')}
- Amount: ${transaction.get('amount', 0):,.2f}
- Current Entity: {transaction.get('classified_entity', 'Unclassified')}
- Current Category: {transaction.get('accounting_category', 'Unclassified')}
- Current Justification: {transaction.get('justification', 'None')}
- Current Confidence: {transaction.get('confidence', 0.5)}

BUSINESS CONTEXT:
{business_knowledge}

SIMILAR TRANSACTIONS (USER-CONFIRMED):
"""

        if similar_transactions:
            for idx, st in enumerate(similar_transactions[:5], 1):
                prompt += f"\n{idx}. Description: {st['description']}"
                prompt += f"\n   Amount: ${st['amount']:,.2f}"
                prompt += f"\n   Entity: {st['classified_entity']}"
                prompt += f"\n   Category: {st['accounting_category']}"
                prompt += f"\n   Confidence: {st['confidence']}"
                prompt += f"\n   Times Confirmed: {st['user_feedback_count']}"
        else:
            prompt += "\nNo similar user-confirmed transactions found."

        prompt += "\n\nLEARNED PATTERNS:"
        if learned_patterns:
            for idx, pattern in enumerate(learned_patterns[:10], 1):
                prompt += f"\n{idx}. Pattern: {pattern['description_pattern']}"
                prompt += f" → Entity: {pattern['entity']}, Category: {pattern['accounting_category']}"
                prompt += f" (Success rate: {pattern['success_count']}/{pattern['usage_count']})"
        else:
            prompt += "\nNo learned patterns available yet."

        prompt += """

TASK:
Analyze this transaction and provide:
1. A new confidence score (0.0-1.0) based on the context
2. Suggestions for improving the classification (entity, category, justification)
3. Clear reasoning for your assessment
4. Whether human review is recommended

Respond ONLY with valid JSON in this exact format:
{
    "confidence": 0.75,
    "suggestions": [
        {
            "field": "classified_entity",
            "current_value": "current value",
            "suggested_value": "suggested value",
            "reasoning": "why this suggestion",
            "confidence": 0.85
        }
    ],
    "reasoning": "Overall analysis of why confidence should be X",
    "should_review": false
}

Guidelines:
- CRITICAL: If any field is empty, null, "Unclassified", "N/A", "Unknown", or "None", you MUST provide a suggestion for that field, even if confidence is low
- CRITICAL: DO NOT suggest a value that is already the current value (i.e., if suggested_value would be the same as current_value, omit that suggestion entirely)
- For classified transactions, only suggest changes if you're confident (>0.7) they're improvements
- If all fields are properly classified and you have no improvements, return empty suggestions array
- Confidence should reflect certainty based on available context (use lower confidence like 0.5-0.6 if uncertain but still suggest)
- Set should_review=true if transaction is unusual or ambiguous
"""

        return prompt

    def _parse_ai_response(self, response_text: str, transaction: Dict) -> Dict:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response (in case there's extra text)
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]

            result = json.loads(json_str)

            # Validate structure
            if 'confidence' not in result:
                result['confidence'] = float(transaction.get('confidence', 0.5))
            if 'suggestions' not in result:
                result['suggestions'] = []
            if 'reasoning' not in result:
                result['reasoning'] = "AI assessment completed"
            if 'should_review' not in result:
                result['should_review'] = result['confidence'] < 0.7

            # Ensure confidence is in valid range
            result['confidence'] = max(0.0, min(1.0, float(result['confidence'])))

            # CRITICAL FIX: Filter out suggestions where suggested_value equals current_value
            # This prevents suggesting categories that are already applied
            filtered_suggestions = []
            for suggestion in result.get('suggestions', []):
                field = suggestion.get('field')
                suggested_value = suggestion.get('suggested_value', '').strip()

                # Get current value from transaction
                current_value = str(transaction.get(field, '')).strip()

                # Only include suggestion if it's actually different from current value
                if suggested_value and suggested_value != current_value:
                    filtered_suggestions.append(suggestion)
                else:
                    # Log that we filtered out a duplicate suggestion
                    print(f"INFO: Filtered out duplicate suggestion for {field}: '{suggested_value}' (already applied)")

            result['suggestions'] = filtered_suggestions

            return result

        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            return {
                "confidence": float(transaction.get('confidence', 0.5)),
                "suggestions": [],
                "reasoning": f"Could not parse AI response: {str(e)}",
                "should_review": True,
                "raw_response": response_text
            }

    def apply_suggestion(
        self,
        transaction_id: int,
        suggestion: Dict,
        db_conn
    ) -> bool:
        """
        Apply an AI suggestion to a transaction and update confidence.

        Returns True if successful, False otherwise.
        """
        cursor = db_conn.cursor()

        try:
            field = suggestion['field']
            new_value = suggestion['suggested_value']
            suggestion_confidence = suggestion.get('confidence', 0.8)

            # Map field names to database columns
            field_map = {
                'classified_entity': 'classified_entity',
                'accounting_category': 'accounting_category',
                'justification': 'justification'
            }

            if field not in field_map:
                return False

            db_field = field_map[field]

            # Update transaction
            update_query = f"""
                UPDATE transactions
                SET {db_field} = %s,
                    confidence = %s,
                    ai_reassessment_count = ai_reassessment_count + 1,
                    last_ai_review = NOW()
                WHERE transaction_id = %s
            """

            cursor.execute(update_query, (new_value, suggestion_confidence, transaction_id))

            # Add to confidence history
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'confidence': suggestion_confidence,
                'reason': f"AI suggestion applied: {suggestion.get('reasoning', 'No reason')}",
                'method': 'ai_suggestion',
                'field_changed': field
            }

            history_query = """
                UPDATE transactions
                SET confidence_history = confidence_history || %s::jsonb
                WHERE transaction_id = %s
            """
            cursor.execute(history_query, (json.dumps(history_entry), transaction_id))

            db_conn.commit()
            cursor.close()

            return True

        except Exception as e:
            db_conn.rollback()
            cursor.close()
            print(f"Error applying suggestion: {e}")
            return False
