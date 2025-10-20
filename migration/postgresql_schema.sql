-- ===============================================
-- PostgreSQL Schema for Delta CFO Agent
-- Migration from SQLite to Cloud SQL (PostgreSQL)
-- ===============================================

-- Enable UUID extension for better primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_stat_statements for performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ===============================================
-- MAIN TRANSACTIONS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    date DATE,
    description TEXT,
    amount DECIMAL(15, 2),
    currency VARCHAR(10),
    usd_equivalent DECIMAL(15, 2),
    classified_entity TEXT,
    justification TEXT,
    confidence DECIMAL(3, 2), -- 0.00 to 1.00
    classification_reason TEXT,
    origin TEXT,
    destination TEXT,
    identifier TEXT,
    source_file TEXT,
    crypto_amount TEXT,
    conversion_note TEXT,
    accounting_category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_entity ON transactions(classified_entity);
CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount);
CREATE INDEX IF NOT EXISTS idx_transactions_source_file ON transactions(source_file);
CREATE INDEX IF NOT EXISTS idx_transactions_confidence ON transactions(confidence);
CREATE INDEX IF NOT EXISTS idx_transactions_updated_at ON transactions(updated_at);

-- ===============================================
-- INVOICES TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    date DATE NOT NULL,
    vendor_name TEXT,
    total_amount DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    payment_due_date DATE,
    payment_status TEXT DEFAULT 'pending',
    items JSONB, -- Store invoice items as JSON
    raw_text TEXT,
    confidence DECIMAL(3, 2),
    processing_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Additional extracted fields
    vendor_address TEXT,
    vendor_tax_id TEXT,
    vendor_contact TEXT,
    vendor_type TEXT,
    extraction_method TEXT,

    -- Customer information
    customer_name TEXT,
    customer_address TEXT,
    customer_tax_id TEXT,

    -- Foreign key to transactions
    linked_transaction_id TEXT REFERENCES transactions(transaction_id)
);

-- Create indexes for invoices
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date);
CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON invoices(vendor_name);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(payment_status);
CREATE INDEX IF NOT EXISTS idx_invoices_linked_tx ON invoices(linked_transaction_id);
CREATE INDEX IF NOT EXISTS idx_invoices_updated_at ON invoices(updated_at);

-- ===============================================
-- INVOICE EMAIL LOG TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS invoice_email_log (
    id SERIAL PRIMARY KEY,
    email_id TEXT UNIQUE NOT NULL,
    subject TEXT,
    sender TEXT,
    received_at TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    attachments_count INTEGER DEFAULT 0,
    invoices_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for email log
CREATE INDEX IF NOT EXISTS idx_email_log_status ON invoice_email_log(status);
CREATE INDEX IF NOT EXISTS idx_email_log_processed_at ON invoice_email_log(processed_at);
CREATE INDEX IF NOT EXISTS idx_email_log_email_id ON invoice_email_log(email_id);

-- ===============================================
-- TRANSACTION CHANGE HISTORY TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS transaction_history (
    id SERIAL PRIMARY KEY,
    transaction_id TEXT REFERENCES transactions(transaction_id),
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Create indexes for history tracking
CREATE INDEX IF NOT EXISTS idx_history_transaction_id ON transaction_history(transaction_id);
CREATE INDEX IF NOT EXISTS idx_history_changed_at ON transaction_history(changed_at);

-- ===============================================
-- DATABASE CONFIGURATION
-- ===============================================

-- Set timezone to UTC
SET timezone = 'UTC';

-- Note: ALTER SYSTEM commands are not supported in Cloud SQL
-- Connection settings are managed by Google Cloud SQL service
-- Default Cloud SQL PostgreSQL settings are optimized for the instance tier

-- ===============================================
-- FUNCTIONS AND TRIGGERS
-- ===============================================

-- Function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to auto-update timestamps
DROP TRIGGER IF EXISTS update_transactions_updated_at ON transactions;
CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- INITIAL DATA SETUP
-- ===============================================

-- Insert some sample data if tables are empty (optional)
-- This can be removed in production

-- ===============================================
-- VACUUM AND ANALYZE
-- ===============================================

-- Optimize tables after creation
VACUUM ANALYZE transactions;
VACUUM ANALYZE invoices;
VACUUM ANALYZE invoice_email_log;
VACUUM ANALYZE transaction_history;