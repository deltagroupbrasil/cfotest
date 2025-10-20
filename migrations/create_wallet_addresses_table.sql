-- Migration: Create wallet_addresses table
-- Description: Stores known cryptocurrency wallet addresses for classification
-- Date: 2025-10-15

CREATE TABLE IF NOT EXISTS wallet_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    wallet_address VARCHAR(255) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    purpose TEXT,
    wallet_type VARCHAR(50),  -- 'internal', 'exchange', 'customer', 'vendor', etc.
    confidence_score DECIMAL(3,2) DEFAULT 0.90,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    -- Constraints
    CONSTRAINT wallet_addresses_tenant_address_unique UNIQUE (tenant_id, wallet_address),
    CONSTRAINT wallet_addresses_confidence_check CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_tenant ON wallet_addresses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_address ON wallet_addresses(wallet_address);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_entity ON wallet_addresses(entity_name);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_active ON wallet_addresses(is_active);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_wallet_addresses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_wallet_addresses_updated_at
    BEFORE UPDATE ON wallet_addresses
    FOR EACH ROW
    EXECUTE FUNCTION update_wallet_addresses_updated_at();

-- Insert the existing known wallet (from main.py hardcoded value)
INSERT INTO wallet_addresses (
    tenant_id,
    wallet_address,
    entity_name,
    purpose,
    wallet_type,
    confidence_score,
    created_by
) VALUES (
    'delta',
    '0x86cc1529bdf444200f06957ab567b56a385c5e90',
    'Internal Transfer',
    'Routing wallet: Whit Mercado Bitcoin → Brazil Bank',
    'internal',
    1.0,
    'migration'
) ON CONFLICT (tenant_id, wallet_address) DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE wallet_addresses IS 'Stores known cryptocurrency wallet addresses for transaction classification';
COMMENT ON COLUMN wallet_addresses.wallet_address IS 'The blockchain wallet address (e.g., 0x... for Ethereum)';
COMMENT ON COLUMN wallet_addresses.entity_name IS 'The business entity or person associated with this wallet';
COMMENT ON COLUMN wallet_addresses.purpose IS 'Description of what this wallet is used for';
COMMENT ON COLUMN wallet_addresses.wallet_type IS 'Category: internal, exchange, customer, vendor, etc.';
COMMENT ON COLUMN wallet_addresses.confidence_score IS 'Confidence level for classification (0.0 to 1.0)';
