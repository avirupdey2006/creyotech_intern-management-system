-- =============================================================================
-- INTERN MANAGEMENT SYSTEM (IMS) - POSTGRESQL SCHEMA (NEON)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 4.1 Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('CANDIDATE', 'HR_REVIEWER', 'ADMIN')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.2 Intern Profiles Table
CREATE TABLE IF NOT EXISTS intern_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    phone_number TEXT NOT NULL, -- Stored encrypted via Fernet (PII encryption at rest)
    college_name VARCHAR(255) NOT NULL,
    internship_role VARCHAR(150) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    application_status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED' CHECK (
        application_status IN (
            'SUBMITTED',
            'IDENTITY_VERIFIED',
            'PROVISIONAL_APPROVED',
            'FINAL_APPROVED',
            'COMPLETED',
            'REJECTED'
        )
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_intern_dates CHECK (end_date >= start_date)
);

-- 4.3 Verification Logs Table (Stores cryptographic reference hashes ONLY; zero raw ID digits)
CREATE TABLE IF NOT EXISTS verification_logs (
    verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES intern_profiles(profile_id) ON DELETE CASCADE,
    gateway_provider VARCHAR(100) NOT NULL,
    transaction_reference VARCHAR(255) UNIQUE NOT NULL, -- HMAC-SHA256 cryptographic hash
    status VARCHAR(50) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING')),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.4 Documents Table
CREATE TABLE IF NOT EXISTS documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES intern_profiles(profile_id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL CHECK (
        document_type IN ('PROVISIONAL_OFFER', 'FINAL_OFFER', 'COMPLETION_CERTIFICATE')
    ),
    storage_path TEXT NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    admin_approved_by UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.5 Audit Logs Table (Immutable system state change trail)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(150) NOT NULL,
    target_entity VARCHAR(150) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Mandatory Performance Indexes (Specification Section 4)
CREATE INDEX IF NOT EXISTS idx_profiles_status ON intern_profiles(application_status);
CREATE INDEX IF NOT EXISTS idx_documents_profile ON documents(profile_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs("timestamp");