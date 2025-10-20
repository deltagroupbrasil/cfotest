#!/usr/bin/env python3
"""
Delta CFO Agent - Web Dashboard
Interactive web interface for financial transaction management
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import random

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

def load_master_transactions():
    """Load transactions from MASTER_TRANSACTIONS.csv"""
    try:
        master_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'MASTER_TRANSACTIONS.csv')
        if os.path.exists(master_file):
            df = pd.read_csv(master_file)
            return df
        else:
            return pd.DataFrame()  # Return empty DataFrame if file doesn't exist
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return pd.DataFrame()

def get_dashboard_stats(df):
    """Calculate dashboard statistics"""
    if df.empty:
        return {
            'total_transactions': 0,
            'total_revenue': 0,
            'total_expenses': 0,
            'needs_review': 0,
            'date_range': {'min': 'N/A', 'max': 'N/A'},
            'entities': [],
            'source_files': []
        }

    # Convert Amount to numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    # Calculate totals
    revenue_df = df[df['Amount'] > 0]
    expense_df = df[df['Amount'] < 0]

    total_revenue = revenue_df['Amount'].sum() if not revenue_df.empty else 0
    total_expenses = abs(expense_df['Amount'].sum()) if not expense_df.empty else 0

    # Count transactions needing review (low confidence or no classification)
    needs_review = 0
    if 'confidence' in df.columns:
        needs_review = len(df[(df['confidence'] < 0.8) | (df['confidence'].isna())])

    # Date range
    date_range = {'min': 'N/A', 'max': 'N/A'}
    if 'Date' in df.columns and not df['Date'].isna().all():
        date_range = {
            'min': df['Date'].min(),
            'max': df['Date'].max()
        }

    # Entity counts
    entities = []
    if 'classified_entity' in df.columns:
        entity_counts = df['classified_entity'].value_counts()
        entities = [(entity, count) for entity, count in entity_counts.items()]

    # Source file counts
    source_files = []
    if 'source_file' in df.columns:
        source_counts = df['source_file'].value_counts()
        source_files = [(source, count) for source, count in source_counts.items()]

    return {
        'total_transactions': len(df),
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'needs_review': needs_review,
        'date_range': date_range,
        'entities': entities[:10],  # Top 10
        'source_files': source_files[:10]  # Top 10
    }

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        df = load_master_transactions()
        stats = get_dashboard_stats(df)

        # Add cache buster for static files
        cache_buster = str(random.randint(1000, 9999))

        return render_template('dashboard.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/api/transactions')
def api_transactions():
    """API endpoint to get filtered transactions"""
    try:
        df = load_master_transactions()

        if df.empty:
            return jsonify([])

        # Apply filters from query parameters
        entity_filter = request.args.get('entity')
        transaction_type = request.args.get('transaction_type')
        source_filter = request.args.get('source_file')
        needs_review = request.args.get('needs_review')
        min_amount = request.args.get('min_amount')
        max_amount = request.args.get('max_amount')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        keyword_filter = request.args.get('keyword')

        # Apply filters
        if entity_filter:
            df = df[df['classified_entity'] == entity_filter]

        if transaction_type == 'Revenue':
            df = df[df['Amount'] > 0]
        elif transaction_type == 'Expense':
            df = df[df['Amount'] < 0]

        if source_filter:
            df = df[df['source_file'] == source_filter]

        if needs_review == 'true' and 'confidence' in df.columns:
            df = df[(df['confidence'] < 0.8) | (df['confidence'].isna())]

        if min_amount:
            df = df[abs(df['Amount']) >= float(min_amount)]

        if max_amount:
            df = df[abs(df['Amount']) <= float(max_amount)]

        if keyword_filter:
            # Search in description and other text fields
            search_cols = ['Description', 'classified_entity', 'keywords_action_type', 'keywords_platform']
            search_cols = [col for col in search_cols if col in df.columns]

            mask = False
            for col in search_cols:
                mask = mask | df[col].astype(str).str.contains(keyword_filter, case=False, na=False)
            df = df[mask]

        # Convert to JSON-serializable format
        transactions = []
        for _, row in df.iterrows():
            transaction = {}
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    transaction[col] = None
                elif isinstance(value, (int, float)):
                    transaction[col] = value
                else:
                    transaction[col] = str(value)
            transactions.append(transaction)

        return jsonify(transactions)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint to get dashboard statistics"""
    try:
        df = load_master_transactions()
        stats = get_dashboard_stats(df)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard_page():
    """Dashboard page (alias for main page)"""
    return dashboard()

@app.route('/revenue')
def revenue_page():
    """Revenue Recognition page"""
    try:
        df = load_master_transactions()
        stats = get_dashboard_stats(df)
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard.html', stats=stats, cache_buster=cache_buster, page_type='revenue')
    except Exception as e:
        return f"Error loading revenue page: {str(e)}", 500

@app.route('/invoices')
def invoices_page():
    """Invoices management page"""
    try:
        df = load_master_transactions()
        stats = get_dashboard_stats(df)
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard.html', stats=stats, cache_buster=cache_buster, page_type='invoices')
    except Exception as e:
        return f"Error loading invoices page: {str(e)}", 500

@app.route('/files')
def files_page():
    """File Manager page"""
    try:
        df = load_master_transactions()
        stats = get_dashboard_stats(df)
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard.html', stats=stats, cache_buster=cache_buster, page_type='files')
    except Exception as e:
        return f"Error loading files page: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)