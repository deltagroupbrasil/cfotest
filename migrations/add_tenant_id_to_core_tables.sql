-- ============================================================================
-- Multi-Tenant Architecture Migration for Core Tables
-- ============================================================================
-- This migration adds tenant_id to all core tables for proper SaaS isolation
-- Author: Claude Code
-- Date: 2025-10-14
-- ============================================================================

-- ============================================================================
-- STEP 1: Add tenant_id to transactions table
-- ============================================================================

-- Add tenant_id column (defaults to 'delta' for existing data)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;

-- Create index on tenant_id for fast tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_id
ON transactions(tenant_id);

-- Create composite indexes for common tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_date
ON transactions(tenant_id, date);

CREATE INDEX IF NOT EXISTS idx_transactions_tenant_entity
ON transactions(tenant_id, classified_entity);

CREATE INDEX IF NOT EXISTS idx_transactions_tenant_category
ON transactions(tenant_id, accounting_category);

-- Add comment
COMMENT ON COLUMN transactions.tenant_id IS 'Tenant identifier for multi-tenant isolation';

-- ============================================================================
-- STEP 2: Add tenant_id to invoices table
-- ============================================================================

-- Add tenant_id column (defaults to 'delta' for existing data)
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;

-- Create index on tenant_id for fast tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_id
ON invoices(tenant_id);

-- Create composite indexes for common tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_date
ON invoices(tenant_id, date);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_vendor
ON invoices(tenant_id, vendor_name);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_status
ON invoices(tenant_id, status);

-- Add comment
COMMENT ON COLUMN invoices.tenant_id IS 'Tenant identifier for multi-tenant isolation';

-- ============================================================================
-- STEP 3: Add tenant_id to transaction_history table
-- ============================================================================

-- Add tenant_id column (defaults to 'delta' for existing data)
ALTER TABLE transaction_history
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;

-- Create index on tenant_id for fast tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_transaction_history_tenant_id
ON transaction_history(tenant_id);

-- Create composite index for tenant + transaction lookups
CREATE INDEX IF NOT EXISTS idx_transaction_history_tenant_tx
ON transaction_history(tenant_id, transaction_id);

-- Add comment
COMMENT ON COLUMN transaction_history.tenant_id IS 'Tenant identifier for multi-tenant isolation';

-- ============================================================================
-- STEP 4: Add tenant_id to invoice_email_log table (if exists)
-- ============================================================================

-- Check if table exists and add tenant_id
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_email_log') THEN
        -- Add tenant_id column (defaults to 'delta' for existing data)
        ALTER TABLE invoice_email_log
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;

        -- Create index on tenant_id for fast tenant-filtered queries
        CREATE INDEX IF NOT EXISTS idx_invoice_email_log_tenant_id
        ON invoice_email_log(tenant_id);

        -- Add comment
        COMMENT ON COLUMN invoice_email_log.tenant_id IS 'Tenant identifier for multi-tenant isolation';

        RAISE NOTICE '✓ Added tenant_id to invoice_email_log table';
    ELSE
        RAISE NOTICE '⚠ Table invoice_email_log does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Create helper functions for tenant operations
-- ============================================================================

-- Function to get tenant_id from a transaction (useful for history tracking)
CREATE OR REPLACE FUNCTION get_transaction_tenant_id(p_transaction_id TEXT)
RETURNS VARCHAR(100) AS $$
DECLARE
    v_tenant_id VARCHAR(100);
BEGIN
    SELECT tenant_id INTO v_tenant_id
    FROM transactions
    WHERE transaction_id = p_transaction_id;

    RETURN v_tenant_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_transaction_tenant_id IS
'Helper function to retrieve tenant_id for a given transaction';

-- Function to validate tenant access (returns TRUE if transaction belongs to tenant)
CREATE OR REPLACE FUNCTION validate_tenant_access(
    p_transaction_id TEXT,
    p_tenant_id VARCHAR(100)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM transactions
    WHERE transaction_id = p_transaction_id
      AND tenant_id = p_tenant_id;

    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_tenant_access IS
'Validates that a transaction belongs to the specified tenant';

-- ============================================================================
-- STEP 6: Create Row Level Security (RLS) policies for tenant isolation
-- ============================================================================
-- Note: RLS is commented out for now to avoid breaking existing code
-- Uncomment when authentication system is fully implemented

-- Enable RLS on transactions table
-- ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation on transactions
-- CREATE POLICY transactions_tenant_isolation ON transactions
--     FOR ALL
--     USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::VARCHAR);

-- Enable RLS on invoices table
-- ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation on invoices
-- CREATE POLICY invoices_tenant_isolation ON invoices
--     FOR ALL
--     USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::VARCHAR);

-- Enable RLS on transaction_history table
-- ALTER TABLE transaction_history ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation on transaction_history
-- CREATE POLICY transaction_history_tenant_isolation ON transaction_history
--     FOR ALL
--     USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::VARCHAR);

-- ============================================================================
-- STEP 7: Update existing triggers to handle tenant_id
-- ============================================================================

-- Update the transaction history trigger to capture tenant_id
CREATE OR REPLACE FUNCTION log_transaction_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Log changes to transaction_history table
    IF (TG_OP = 'UPDATE') THEN
        -- Insert history record with tenant_id from the transaction
        INSERT INTO transaction_history (
            transaction_id,
            tenant_id,
            field_name,
            old_value,
            new_value,
            changed_by,
            change_reason
        )
        SELECT
            NEW.transaction_id,
            NEW.tenant_id,  -- Capture tenant_id
            key,
            old_row.value::TEXT,
            new_row.value::TEXT,
            NEW.updated_by,
            'Automatic change tracking'
        FROM jsonb_each(to_jsonb(OLD)) AS old_row
        JOIN jsonb_each(to_jsonb(NEW)) AS new_row ON old_row.key = new_row.key
        WHERE old_row.value IS DISTINCT FROM new_row.value
          AND old_row.key NOT IN ('updated_at', 'updated_by');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate trigger
DROP TRIGGER IF EXISTS trigger_log_transaction_change ON transactions;
CREATE TRIGGER trigger_log_transaction_change
    AFTER UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION log_transaction_change();

-- ============================================================================
-- STEP 8: Verify migration
-- ============================================================================

-- Check that all tables have tenant_id column
DO $$
DECLARE
    v_tables TEXT[] := ARRAY['transactions', 'invoices', 'transaction_history', 'invoice_email_log'];
    v_table TEXT;
    v_count INTEGER;
BEGIN
    RAISE NOTICE '=== Verifying tenant_id columns ===';

    FOREACH v_table IN ARRAY v_tables
    LOOP
        SELECT COUNT(*) INTO v_count
        FROM information_schema.columns
        WHERE table_name = v_table
          AND column_name = 'tenant_id';

        IF v_count > 0 THEN
            RAISE NOTICE '✓ Table % has tenant_id column', v_table;
        ELSE
            RAISE WARNING '✗ Table % is missing tenant_id column', v_table;
        END IF;
    END LOOP;

    RAISE NOTICE '=== Verification complete ===';
END $$;

-- ============================================================================
-- Migration Summary
-- ============================================================================
--
-- Changes applied:
-- ✓ Added tenant_id to transactions table with default 'delta'
-- ✓ Added tenant_id to invoices table with default 'delta'
-- ✓ Added tenant_id to transaction_history table with default 'delta'
-- ✓ Added tenant_id to invoice_email_log table with default 'delta'
-- ✓ Created indexes for tenant-filtered queries on all tables
-- ✓ Created helper functions for tenant operations
-- ✓ Prepared RLS policies (commented out, ready for authentication)
-- ✓ Updated triggers to handle tenant_id in history tracking
--
-- Next steps:
-- 1. Update application code to include tenant_id in all INSERT statements
-- 2. Update application code to filter by tenant_id in all SELECT statements
-- 3. Implement session/JWT-based tenant_id capture
-- 4. Enable Row Level Security when authentication is implemented
-- 5. Test multi-tenant isolation thoroughly
--
-- ============================================================================
