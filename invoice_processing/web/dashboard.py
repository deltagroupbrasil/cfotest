#!/usr/bin/env python3
"""
Invoice Dashboard - Analytics and Management
Dashboard para visualização e gestão de faturas processadas
"""

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from integration import MainSystemIntegrator
from core.delta_classifier import DeltaBusinessClassifier

app = Flask(__name__, template_folder='templates', static_folder='static')

class InvoiceDashboard:
    """Dashboard analytics for processed invoices"""

    def __init__(self):
        self.integrator = MainSystemIntegrator()
        self.classifier = DeltaBusinessClassifier()

    def get_dashboard_data(self, days: int = 30) -> dict:
        """Get comprehensive dashboard data"""
        try:
            # Get recent invoices
            invoices = self.integrator.get_invoices(limit=100)

            # Filter by date range if needed
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                invoices = [inv for inv in invoices if
                           datetime.fromisoformat(inv.get('created_at', '2024-01-01')) > cutoff_date]

            # Calculate analytics
            analytics = self._calculate_analytics(invoices)

            # Business unit breakdown
            bu_breakdown = self._analyze_business_units(invoices)

            # Category analysis
            category_analysis = self._analyze_categories(invoices)

            # Crypto vs Fiat analysis
            currency_analysis = self._analyze_currency_types(invoices)

            # Recent activity
            recent_activity = invoices[:10]  # Last 10 invoices

            # Confidence analysis
            confidence_analysis = self._analyze_confidence_scores(invoices)

            return {
                'summary': analytics,
                'business_units': bu_breakdown,
                'categories': category_analysis,
                'currencies': currency_analysis,
                'recent_activity': recent_activity,
                'confidence_analysis': confidence_analysis,
                'total_invoices': len(invoices),
                'date_range': f"Last {days} days"
            }

        except Exception as e:
            print(f"Dashboard data error: {e}")
            return {'error': str(e)}

    def _calculate_analytics(self, invoices: list) -> dict:
        """Calculate summary analytics"""
        if not invoices:
            return {'total_amount': 0, 'avg_amount': 0, 'count': 0}

        total_amount = sum(float(inv.get('total_amount', 0)) for inv in invoices)
        avg_amount = total_amount / len(invoices) if invoices else 0

        # Status breakdown
        status_counts = {}
        for inv in invoices:
            status = inv.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'total_amount': round(total_amount, 2),
            'avg_amount': round(avg_amount, 2),
            'count': len(invoices),
            'status_breakdown': status_counts
        }

    def _analyze_business_units(self, invoices: list) -> dict:
        """Analyze business unit distribution"""
        bu_data = {}

        for inv in invoices:
            bu = inv.get('business_unit', 'Unknown')
            amount = float(inv.get('total_amount', 0))

            if bu not in bu_data:
                bu_data[bu] = {'count': 0, 'total_amount': 0, 'invoices': []}

            bu_data[bu]['count'] += 1
            bu_data[bu]['total_amount'] += amount
            bu_data[bu]['invoices'].append(inv['id'])

        # Calculate percentages
        total_amount = sum(data['total_amount'] for data in bu_data.values())
        total_count = sum(data['count'] for data in bu_data.values())

        for bu, data in bu_data.items():
            data['amount_percentage'] = (data['total_amount'] / total_amount * 100) if total_amount > 0 else 0
            data['count_percentage'] = (data['count'] / total_count * 100) if total_count > 0 else 0
            data['avg_amount'] = data['total_amount'] / data['count'] if data['count'] > 0 else 0

        return bu_data

    def _analyze_categories(self, invoices: list) -> dict:
        """Analyze expense categories"""
        category_data = {}

        for inv in invoices:
            category = inv.get('category', 'Unknown')
            amount = float(inv.get('total_amount', 0))

            if category not in category_data:
                category_data[category] = {'count': 0, 'total_amount': 0}

            category_data[category]['count'] += 1
            category_data[category]['total_amount'] += amount

        return category_data

    def _analyze_currency_types(self, invoices: list) -> dict:
        """Analyze cryptocurrency vs fiat distribution"""
        currency_data = {'cryptocurrency': {'count': 0, 'total_amount': 0},
                        'fiat': {'count': 0, 'total_amount': 0}}

        for inv in invoices:
            currency_type = inv.get('currency_type', 'fiat')
            amount = float(inv.get('total_amount', 0))

            if currency_type in currency_data:
                currency_data[currency_type]['count'] += 1
                currency_data[currency_type]['total_amount'] += amount

        return currency_data

    def _analyze_confidence_scores(self, invoices: list) -> dict:
        """Analyze AI confidence scores"""
        confidence_ranges = {
            'high': {'range': '90-100%', 'count': 0},
            'medium': {'range': '70-89%', 'count': 0},
            'low': {'range': '50-69%', 'count': 0},
            'very_low': {'range': '<50%', 'count': 0}
        }

        for inv in invoices:
            confidence = float(inv.get('confidence_score', 0.8))

            if confidence >= 0.9:
                confidence_ranges['high']['count'] += 1
            elif confidence >= 0.7:
                confidence_ranges['medium']['count'] += 1
            elif confidence >= 0.5:
                confidence_ranges['low']['count'] += 1
            else:
                confidence_ranges['very_low']['count'] += 1

        return confidence_ranges

    def get_business_unit_details(self, business_unit: str) -> dict:
        """Get detailed information for a specific business unit"""
        try:
            # Get invoices for this business unit
            invoices = self.integrator.get_invoices(
                filters={'business_unit': business_unit},
                limit=50
            )

            # Get business unit info from classifier
            bu_info = self.classifier.get_business_unit_info(business_unit)

            # Calculate metrics
            total_amount = sum(float(inv.get('total_amount', 0)) for inv in invoices)
            avg_amount = total_amount / len(invoices) if invoices else 0

            # Category breakdown for this BU
            categories = {}
            for inv in invoices:
                cat = inv.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

            return {
                'business_unit': business_unit,
                'info': bu_info,
                'metrics': {
                    'total_invoices': len(invoices),
                    'total_amount': round(total_amount, 2),
                    'avg_amount': round(avg_amount, 2)
                },
                'categories': categories,
                'recent_invoices': invoices[:10]
            }

        except Exception as e:
            return {'error': str(e)}

dashboard_handler = InvoiceDashboard()

# Flask Routes
@app.route('/dashboard')
def dashboard():
    """Main dashboard view"""
    days = request.args.get('days', 30, type=int)
    data = dashboard_handler.get_dashboard_data(days)

    if 'error' in data:
        return f"Dashboard Error: {data['error']}", 500

    return render_template('invoice_dashboard.html', data=data)

@app.route('/api/dashboard/data')
def api_dashboard_data():
    """API endpoint for dashboard data"""
    days = request.args.get('days', 30, type=int)
    data = dashboard_handler.get_dashboard_data(days)
    return jsonify(data)

@app.route('/api/business-unit/<business_unit>')
def api_business_unit_details(business_unit):
    """API endpoint for business unit details"""
    data = dashboard_handler.get_business_unit_details(business_unit)
    return jsonify(data)

@app.route('/invoices/list')
def invoice_list():
    """Invoice list view"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    invoices = dashboard_handler.integrator.get_invoices(
        limit=limit,
        offset=(page - 1) * limit
    )

    return render_template('invoice_list.html', invoices=invoices, page=page)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5004))
    print("🚀 Invoice Dashboard starting...")
    print(f"   Dashboard: http://localhost:{port}/dashboard")
    print(f"   Invoice List: http://localhost:{port}/invoices/list")
    app.run(host='0.0.0.0', port=port, debug=True)