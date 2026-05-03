-- Migration: Add Multi-Tenancy Support
-- This migration transforms the database from single-tenant to multi-tenant
-- It's designed to run without downtime

-- ============================================
-- 1. CREATE ORGANIZATION TABLES
-- ============================================

-- Organizations table (new)
CREATE TABLE IF NOT EXISTS organizations (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  tier VARCHAR(50) DEFAULT 'free' NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_is_active ON organizations(is_active);

-- Organization members table (new)
CREATE TABLE IF NOT EXISTS organization_members (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) DEFAULT 'member' NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON organization_members(user_id);

-- API Keys table (new)
CREATE TABLE IF NOT EXISTS api_keys (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  key_hash VARCHAR(255) UNIQUE NOT NULL,
  last_used TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_org_id ON api_keys(organization_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- ============================================
-- 2. MODIFY EXISTING TABLES FOR MULTI-TENANCY
-- ============================================

-- Add organization_id to users table (optional, for future use)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE NOT NULL DEFAULT '';

-- Add organization_id to prediction_records
ALTER TABLE prediction_records ADD COLUMN IF NOT EXISTS organization_id INTEGER;

-- Temporarily allow NULL for migration
ALTER TABLE prediction_records ALTER COLUMN organization_id DROP NOT NULL;

-- Add foreign key
ALTER TABLE prediction_records ADD CONSTRAINT IF NOT EXISTS fk_pred_org
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Create composite indexes for org isolation
CREATE INDEX IF NOT EXISTS idx_pred_org_user_id ON prediction_records(organization_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pred_org_timestamp ON prediction_records(organization_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_pred_org_archived ON prediction_records(organization_id, archived);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pred_org_request_id ON prediction_records(organization_id, request_id);

-- Add organization_id to model_metrics
ALTER TABLE model_metrics ADD COLUMN IF NOT EXISTS organization_id INTEGER;

-- Temporarily allow NULL for migration
ALTER TABLE model_metrics ALTER COLUMN organization_id DROP NOT NULL;

-- Add foreign key
ALTER TABLE model_metrics ADD CONSTRAINT IF NOT EXISTS fk_metrics_org
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Create composite indexes
CREATE INDEX IF NOT EXISTS idx_metrics_org_user_date ON model_metrics(organization_id, user_id, date);
CREATE INDEX IF NOT EXISTS idx_metrics_org_date ON model_metrics(organization_id, date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_metrics_org_user_date ON model_metrics(organization_id, user_id, date);

-- ============================================
-- 3. CREATE BILLING TABLES
-- ============================================

-- Subscription tiers
CREATE TABLE IF NOT EXISTS subscription_tiers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  price_usd INTEGER DEFAULT 0,
  requests_per_month INTEGER NOT NULL,
  batch_limit INTEGER DEFAULT 100,
  rate_limit_rpm INTEGER DEFAULT 1000,
  features TEXT DEFAULT ''
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
  tier_id INTEGER NOT NULL REFERENCES subscription_tiers(id),
  status VARCHAR(50) DEFAULT 'active' NOT NULL,
  stripe_subscription_id VARCHAR(255) UNIQUE,
  stripe_customer_id VARCHAR(255),
  billing_cycle_start TIMESTAMP DEFAULT NOW(),
  billing_cycle_end TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subs_org_id ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subs_stripe_id ON subscriptions(stripe_subscription_id);

-- Usage quotas
CREATE TABLE IF NOT EXISTS usage_quotas (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
  tier_id INTEGER NOT NULL REFERENCES subscription_tiers(id),
  requests_used_this_month INTEGER DEFAULT 0,
  billing_period_start TIMESTAMP DEFAULT NOW(),
  billing_period_end TIMESTAMP NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quota_org_id ON usage_quotas(organization_id);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
  stripe_invoice_id VARCHAR(255) UNIQUE,
  amount_cents INTEGER NOT NULL,
  status VARCHAR(50) DEFAULT 'draft' NOT NULL,
  period_start TIMESTAMP NOT NULL,
  period_end TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  paid_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoice_org_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoices(status);

-- ============================================
-- 4. DATA MIGRATION: Create default organization
-- ============================================

-- Create default organization for existing data
INSERT INTO organizations (name, slug, tier, is_active)
VALUES ('Default Organization', 'default-org', 'free', TRUE)
ON CONFLICT (slug) DO NOTHING;

-- Get the default org ID
DO $$
DECLARE
  default_org_id INTEGER;
BEGIN
  SELECT id INTO default_org_id FROM organizations WHERE slug = 'default-org' LIMIT 1;

  -- Migrate existing users to default org membership
  INSERT INTO organization_members (organization_id, user_id, role)
  SELECT default_org_id, id, 'admin' FROM users
  ON CONFLICT (organization_id, user_id) DO NOTHING;

  -- Migrate existing predictions to default org
  UPDATE prediction_records
  SET organization_id = default_org_id
  WHERE organization_id IS NULL;

  -- Migrate existing metrics to default org
  UPDATE model_metrics
  SET organization_id = default_org_id
  WHERE organization_id IS NULL;

  -- Create default subscription tier
  INSERT INTO subscription_tiers (name, price_usd, requests_per_month, batch_limit, rate_limit_rpm)
  VALUES
    ('free', 0, 1000, 50, 10),
    ('pro', 2900, 100000, 10000, 100),
    ('business', 29900, 1000000, 50000, 1000),
    ('enterprise', 0, 999999999, 999999999, 999999999)
  ON CONFLICT (name) DO NOTHING;

  -- Create default subscription for default org
  INSERT INTO subscriptions (organization_id, tier_id, status)
  SELECT default_org_id, id, 'active' FROM subscription_tiers WHERE name = 'free'
  ON CONFLICT (organization_id) DO NOTHING;

  -- Create default usage quota
  INSERT INTO usage_quotas (organization_id, tier_id, billing_period_end)
  SELECT default_org_id, id, NOW() + INTERVAL '30 days' FROM subscription_tiers WHERE name = 'free'
  ON CONFLICT (organization_id) DO NOTHING;
END $$;

-- ============================================
-- 5. ENFORCE NOT NULL CONSTRAINTS
-- ============================================

-- Now that we've migrated data, make organization_id NOT NULL
ALTER TABLE prediction_records ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE model_metrics ALTER COLUMN organization_id SET NOT NULL;

-- ============================================
-- 6. DROP OLD VIEWS (if they exist) AND CREATE NEW ONES
-- ============================================

-- Drop old views
DROP VIEW IF EXISTS recent_predictions CASCADE;
DROP VIEW IF EXISTS daily_statistics CASCADE;

-- Create new org-scoped views
CREATE OR REPLACE VIEW recent_predictions AS
SELECT
  pr.id,
  pr.organization_id,
  u.username,
  pr.input_text,
  pr.prediction,
  pr.confidence,
  pr.inference_time_ms,
  pr.timestamp
FROM prediction_records pr
JOIN users u ON pr.user_id = u.id
WHERE pr.timestamp > NOW() - INTERVAL '7 days'
  AND pr.archived = FALSE
ORDER BY pr.timestamp DESC;

CREATE OR REPLACE VIEW daily_statistics AS
SELECT
  mm.organization_id,
  u.username,
  mm.date,
  mm.predictions_count,
  mm.avg_confidence,
  mm.avg_inference_time_ms
FROM model_metrics mm
JOIN users u ON mm.user_id = u.id
ORDER BY mm.date DESC;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- The database is now multi-tenant!
-- All existing data is in the default organization.
-- New organizations can be created for additional tenants.
