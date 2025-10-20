#!/usr/bin/env python3
"""
Invoice Processing Module Configuration
Isolated settings that don't interfere with main system
"""

import os
from pathlib import Path

# Module Configuration
MODULE_VERSION = "1.0.0"
MODULE_NAME = "Invoice Processing"

# File Paths (Isolated from main system)
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "invoices"
PROCESSED_DIR = BASE_DIR / "processed" / "invoices"
FAILED_DIR = BASE_DIR / "failed" / "invoices"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration (Uses main DB but separate tables)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///delta_transactions.db')

# Email Configuration
EMAIL_SETTINGS = {
    'IMAP_SERVER': os.getenv('IMAP_SERVER', 'imap.gmail.com'),
    'IMAP_PORT': int(os.getenv('IMAP_PORT', 993)),
    'EMAIL_ADDRESS': os.getenv('INVOICE_EMAIL', ''),
    'EMAIL_PASSWORD': os.getenv('INVOICE_EMAIL_PASSWORD', ''),
    'INBOX_FOLDER': os.getenv('INBOX_FOLDER', 'INBOX'),
    'PROCESSED_FOLDER': os.getenv('PROCESSED_FOLDER', 'Processed'),
    'CHECK_INTERVAL': int(os.getenv('EMAIL_CHECK_INTERVAL', 300))  # 5 minutes
}

# Claude API Configuration (Separate from main system)
CLAUDE_CONFIG = {
    'API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
    'MODEL': 'claude-3-haiku-20240307',  # Fast model for vision
    'MAX_TOKENS': 4000,
    'TEMPERATURE': 0.1  # Low temperature for structured data
}

# Processing Configuration
PROCESSING_CONFIG = {
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_EXTENSIONS': {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'},
    'OCR_LANGUAGE': 'eng+por',  # English + Portuguese
    'BATCH_SIZE': 5,  # Process 5 invoices at once
    'RETRY_ATTEMPTS': 3
}

# Integration Points with Main System
INTEGRATION_CONFIG = {
    'DATABASE_TABLE': 'invoices',  # Separate table
    'WEB_ROUTE_PREFIX': '/invoices',  # Isolated web routes
    'API_ENDPOINT_PREFIX': '/api/v1/invoices'  # Isolated API endpoints
}

# Logging Configuration
LOGGING_CONFIG = {
    'LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
    'FILE': BASE_DIR / 'logs' / 'invoice_processing.log',
    'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# Ensure logs directory exists
(BASE_DIR / 'logs').mkdir(exist_ok=True)

# Invoice Field Mapping
INVOICE_FIELDS = {
    'required': [
        'invoice_number',
        'date',
        'vendor_name',
        'total_amount',
        'currency'
    ],
    'optional': [
        'due_date',
        'tax_amount',
        'line_items',
        'vendor_address',
        'vendor_tax_id',
        'payment_terms'
    ]
}

# Validation Rules
VALIDATION_RULES = {
    'max_amount': 1000000,  # $1M max
    'min_amount': 0.01,     # $0.01 min
    'date_range_days': 365, # Must be within 1 year
    'required_confidence': 0.8  # 80% confidence minimum
}