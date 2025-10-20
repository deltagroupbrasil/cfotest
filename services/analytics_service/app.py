#!/usr/bin/env python3
"""
Delta CFO Agent - Analytics Microservice
=====================================

Advanced analytics service for financial data insights and reporting.
Provides REST API endpoints for business intelligence and data visualization.
"""

import os
import sys
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
import json
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent.parent))

# Import centralized database manager
from web_ui.database import db_manager

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configuration
PORT = int(os.environ.get('PORT', 8080))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

class AnalyticsEngine:
    """Core analytics engine for financial data processing using PostgreSQL"""

    def __init__(self):
        self.db = db_manager

    def get_db_connection(self):
        """Get database connection using centralized DatabaseManager"""
        try:
            return self.db.get_connection()
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def get_monthly_summary(self, months=12):
        """Get monthly transaction summary"""
        try:
            # PostgreSQL compatible query
            if self.db.db_type == 'postgresql':
                query = """
                SELECT
                    DATE_TRUNC('month', date::date) as month,
                    entity,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                    SUM(amount) as net_flow,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE date::date >= CURRENT_DATE - INTERVAL '%s months'
                GROUP BY month, entity
                ORDER BY month DESC, entity
                """ % months
            else:
                # SQLite fallback
                query = """
                SELECT
                    DATE(date, 'start of month') as month,
                    entity,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                    SUM(amount) as net_flow,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE date >= date('now', '-%s months')
                GROUP BY month, entity
                ORDER BY month DESC, entity
                """ % months

            result = self.db.execute_query(query, fetch_all=True)

            if result:
                # Convert to pandas-like format for compatibility
                summary_data = []
                for row in result:
                    if hasattr(row, '_asdict'):
                        summary_data.append(row._asdict())
                    elif hasattr(row, 'keys'):
                        summary_data.append(dict(row))
                    else:
                        # Handle tuple format
                        keys = ['month', 'entity', 'income', 'expenses', 'net_flow', 'transaction_count']
                        summary_data.append(dict(zip(keys, row)))

                return {
                    'summary': summary_data,
                    'total_months': months,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                return {
                    'summary': [],
                    'total_months': months,
                    'generated_at': datetime.now().isoformat()
                }

        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    def get_entity_breakdown(self):
        """Get transaction breakdown by business entity"""
        try:
            query = """
            SELECT
                entity,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                SUM(amount) as net_position,
                AVG(amount) as avg_transaction_size,
                MIN(date) as first_transaction,
                MAX(date) as last_transaction
            FROM transactions
            GROUP BY entity
            ORDER BY total_transactions DESC
            """

            result = self.db.execute_query(query, fetch_all=True)

            if result:
                # Convert to dictionary format
                entities_data = []
                for row in result:
                    if hasattr(row, '_asdict'):
                        entities_data.append(row._asdict())
                    elif hasattr(row, 'keys'):
                        entities_data.append(dict(row))
                    else:
                        # Handle tuple format
                        keys = ['entity', 'total_transactions', 'total_income', 'total_expenses',
                               'net_position', 'avg_transaction_size', 'first_transaction', 'last_transaction']
                        entities_data.append(dict(zip(keys, row)))

                return {
                    'entities': entities_data,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                return {
                    'entities': [],
                    'generated_at': datetime.now().isoformat()
                }

        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    def get_category_analysis(self):
        """Analyze spending by category"""
        try:
            query = """
            SELECT
                category,
                entity,
                COUNT(*) as transaction_count,
                SUM(ABS(amount)) as total_amount,
                AVG(ABS(amount)) as avg_amount,
                SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as income_transactions,
                SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as expense_transactions
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category, entity
            ORDER BY total_amount DESC
            LIMIT 50
            """

            result = self.db.execute_query(query, fetch_all=True)

            if result:
                # Convert to dictionary format
                categories_data = []
                for row in result:
                    if hasattr(row, '_asdict'):
                        categories_data.append(row._asdict())
                    elif hasattr(row, 'keys'):
                        categories_data.append(dict(row))
                    else:
                        # Handle tuple format
                        keys = ['category', 'entity', 'transaction_count', 'total_amount',
                               'avg_amount', 'income_transactions', 'expense_transactions']
                        categories_data.append(dict(zip(keys, row)))

                return {
                    'categories': categories_data,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                return {
                    'categories': [],
                    'generated_at': datetime.now().isoformat()
                }

        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

# Initialize analytics engine
analytics = AnalyticsEngine()

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'Delta CFO Analytics Service',
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/analytics/monthly-summary')
def monthly_summary():
    """Get monthly transaction summary"""
    months = request.args.get('months', 12, type=int)
    months = min(max(months, 1), 24)  # Limit between 1-24 months

    result = analytics.get_monthly_summary(months)
    return jsonify(result)

@app.route('/api/analytics/entities')
def entity_breakdown():
    """Get transaction breakdown by business entity"""
    result = analytics.get_entity_breakdown()
    return jsonify(result)

@app.route('/api/analytics/categories')
def category_analysis():
    """Get spending analysis by category"""
    result = analytics.get_category_analysis()
    return jsonify(result)

@app.route('/api/analytics/dashboard')
def dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Combine multiple analytics
        monthly = analytics.get_monthly_summary(6)  # Last 6 months
        entities = analytics.get_entity_breakdown()
        categories = analytics.get_category_analysis()

        dashboard = {
            'monthly_summary': monthly,
            'entity_breakdown': entities,
            'category_analysis': categories,
            'generated_at': datetime.now().isoformat(),
            'service_info': {
                'name': 'Delta CFO Analytics Service',
                'version': '1.0.0'
            }
        }

        return jsonify(dashboard)

    except Exception as e:
        return jsonify({'error': f'Dashboard generation failed: {str(e)}'}), 500

@app.route('/api/analytics/status')
def service_status():
    """Get service status and database connectivity"""
    try:
        # Test database connection using DatabaseManager
        result = analytics.db.execute_query("SELECT COUNT(*) FROM transactions", fetch_one=True)

        if result:
            transaction_count = result[0] if isinstance(result, tuple) else result['count']

            return jsonify({
                'service': 'analytics-service',
                'status': 'operational',
                'database': f'connected ({analytics.db.db_type})',
                'transaction_count': transaction_count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'service': 'analytics-service',
                'status': 'degraded',
                'database': 'query_failed',
                'timestamp': datetime.now().isoformat()
            }), 503

    except Exception as e:
        return jsonify({
            'service': 'analytics-service',
            'status': 'error',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/api/analytics/monthly-summary',
            '/api/analytics/entities',
            '/api/analytics/categories',
            '/api/analytics/dashboard',
            '/api/analytics/status'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Analytics service encountered an error'
    }), 500

if __name__ == '__main__':
    print(f"🚀 Starting Delta CFO Analytics Service on port {PORT}")
    print(f"📊 Database: {analytics.db.db_type} (centralized)")
    print(f"🔧 Debug mode: {DEBUG}")

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True
    )