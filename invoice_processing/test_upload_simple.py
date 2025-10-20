#!/usr/bin/env python3
"""
Simple Upload Test - Simplified version for immediate testing
"""

import os
import sys
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import uuid

# Simple Flask app for testing
app = Flask(__name__)
app.secret_key = 'test_secret_key'

# Simple database setup
DB_PATH = Path(__file__).parent / "test_invoices.db"

def init_db():
    """Initialize simple test database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS test_invoices (
            id TEXT PRIMARY KEY,
            filename TEXT,
            upload_time TEXT,
            status TEXT DEFAULT 'uploaded'
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Test database initialized: {DB_PATH}")

# Simple HTML template
UPLOAD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Invoice Upload Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .upload-area { border: 2px dashed #ccc; padding: 50px; text-align: center; margin: 20px 0; }
        .upload-area:hover { border-color: #007bff; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .status { margin: 20px 0; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <h1>🧾 Delta CFO Agent - Invoice Upload Test</h1>
    <p>Sistema simplificado para teste de upload de faturas</p>

    {% if status %}
        <div class="status {{ status.type }}">
            {{ status.message }}
        </div>
    {% endif %}

    <form method="POST" enctype="multipart/form-data">
        <div class="upload-area" onclick="document.getElementById('file').click()">
            <h3>📄 Clique aqui para fazer upload de fatura</h3>
            <p>Formatos suportados: PDF, PNG, JPG</p>
            <input type="file" id="file" name="file" style="display: none" accept=".pdf,.png,.jpg,.jpeg" required>
            <div id="filename"></div>
        </div>
        <button type="submit" class="btn">🚀 Processar Fatura</button>
    </form>

    <script>
        document.getElementById('file').onchange = function() {
            document.getElementById('filename').innerHTML = '<strong>Arquivo selecionado:</strong> ' + this.files[0].name;
        }
    </script>

    <h2>📊 Status do Sistema</h2>
    <ul>
        <li>✅ Database: Conectado</li>
        <li>✅ Upload Interface: Funcionando</li>
        <li>⚠️ Claude Vision: Simulado (teste)</li>
        <li>⚠️ Business Classification: Simulado (teste)</li>
    </ul>

    <h2>📋 Faturas Processadas</h2>
    {% for invoice in recent_invoices %}
        <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0;">
            <strong>{{ invoice[1] }}</strong> - {{ invoice[2] }} - Status: {{ invoice[3] }}
        </div>
    {% endfor %}
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Simple upload form"""
    status = None

    if request.method == 'POST':
        if 'file' not in request.files:
            status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
        else:
            file = request.files['file']
            if file.filename == '':
                status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
            else:
                # Simulate processing
                try:
                    # Save file info to database
                    conn = sqlite3.connect(DB_PATH)
                    invoice_id = str(uuid.uuid4())[:8]
                    conn.execute(
                        "INSERT INTO test_invoices (id, filename, upload_time, status) VALUES (?, ?, ?, ?)",
                        (invoice_id, file.filename, datetime.now().isoformat(), 'processed')
                    )
                    conn.commit()
                    conn.close()

                    status = {'type': 'success', 'message': f'Fatura {file.filename} processada com sucesso! ID: {invoice_id}'}
                except Exception as e:
                    status = {'type': 'error', 'message': f'Erro ao processar: {str(e)}'}

    # Get recent invoices
    try:
        conn = sqlite3.connect(DB_PATH)
        recent_invoices = conn.execute("SELECT * FROM test_invoices ORDER BY upload_time DESC LIMIT 5").fetchall()
        conn.close()
    except:
        recent_invoices = []

    return render_template_string(UPLOAD_TEMPLATE, status=status, recent_invoices=recent_invoices)

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM test_invoices").fetchone()[0]
        conn.close()

        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'total_invoices': count,
            'message': 'Sistema funcionando normalmente'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

if __name__ == '__main__':
    init_db()
    print("Simple Invoice Upload Test starting...")
    print("   Access: http://localhost:5002")
    print("   API Status: http://localhost:5002/api/status")
    print("   Press Ctrl+C to stop")

    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)