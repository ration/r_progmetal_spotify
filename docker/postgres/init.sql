-- PostgreSQL Initialization Script for Album Catalog
-- This script runs automatically when the PostgreSQL container is first created

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database (already created by POSTGRES_DB env var, but included for documentation)
-- Database: progmetal
-- User: progmetal
-- Password: Set via POSTGRES_PASSWORD environment variable

-- Set default timezone
SET timezone = 'UTC';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Album Catalog Database Initialized';
    RAISE NOTICE 'Database: progmetal';
    RAISE NOTICE 'Timestamp: %', NOW();
END $$;
