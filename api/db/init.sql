-- PostgreSQL initialization script with encryption functions for QoE Application

-- Enable pgcrypto extension for encryption/decryption functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create deterministic encryption function for wallet addresses (for upsert functionality)
CREATE OR REPLACE FUNCTION encrypt_wallet(wallet_address TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Use HMAC for deterministic encryption (same input always produces same output)
    -- This allows upsert functionality while still providing security
    RETURN encode(hmac(wallet_address, encryption_key, 'sha256'), 'base64');
END;
$$ LANGUAGE plpgsql;

-- Create decryption function for wallet addresses (admin use only)
-- Note: HMAC is one-way, so this function cannot decrypt HMAC hashes
-- This is kept for compatibility but will only work with old pgp_sym_encrypt data
CREATE OR REPLACE FUNCTION decrypt_wallet(encrypted_wallet TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    -- This function can no longer decrypt HMAC hashes (they are one-way)
    -- Only works with old pgp_sym_encrypt encrypted data
    RETURN pgp_sym_decrypt(decode(encrypted_wallet, 'base64'), encryption_key);
EXCEPTION WHEN OTHERS THEN
    RETURN 'HMAC_HASH_NOT_REVERSIBLE';
END;
$$ LANGUAGE plpgsql;

-- Create upsert function for ratings (one rating per wallet per service)
CREATE OR REPLACE FUNCTION upsert_rating(
    p_service_id INTEGER,
    p_wallet_address TEXT,
    p_rating FLOAT,
    p_feedback TEXT DEFAULT NULL,
    p_encryption_key TEXT DEFAULT 'your-secret-key'
)
RETURNS TABLE(
    rate_id INTEGER,
    service_id INTEGER,
    rating FLOAT,
    feedback TEXT,
    is_new_rating BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
DECLARE
    encrypted_wallet_value TEXT;
    existing_rate_id INTEGER;
    result_record RECORD;
BEGIN
    -- Encrypt the wallet address
    encrypted_wallet_value := encrypt_wallet(p_wallet_address, p_encryption_key);
    
    -- Check if rating already exists for this service and wallet
    SELECT id INTO existing_rate_id 
    FROM rates 
    WHERE rates.service_id = p_service_id 
    AND rates.encrypted_wallet = encrypted_wallet_value;
    
    IF existing_rate_id IS NOT NULL THEN
        -- Update existing rating
        UPDATE rates 
        SET rating = p_rating,
            feedback = COALESCE(p_feedback, rates.feedback),
            updated_at = NOW()
        WHERE rates.id = existing_rate_id
        RETURNING rates.id, rates.service_id, rates.rating, rates.feedback, rates.created_at, rates.updated_at
        INTO result_record;
        
        RETURN QUERY SELECT 
            result_record.id,
            result_record.service_id,
            result_record.rating,
            result_record.feedback,
            FALSE as is_new_rating,
            result_record.created_at,
            result_record.updated_at;
    ELSE
        -- Insert new rating
        INSERT INTO rates (service_id, encrypted_wallet, rating, feedback, created_at, updated_at)
        VALUES (p_service_id, encrypted_wallet_value, p_rating, p_feedback, NOW(), NOW())
        RETURNING rates.id, rates.service_id, rates.rating, rates.feedback, rates.created_at, rates.updated_at
        INTO result_record;
        
        RETURN QUERY SELECT 
            result_record.id,
            result_record.service_id,
            result_record.rating,
            result_record.feedback,
            TRUE as is_new_rating,
            result_record.created_at,
            result_record.updated_at;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to calculate service score and rating distribution
CREATE OR REPLACE FUNCTION calculate_service_score(p_service_id INTEGER)
RETURNS TABLE(
    service_id INTEGER,
    average_rating FLOAT,
    total_ratings INTEGER,
    rating_distribution JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p_service_id,
        ROUND(AVG(rating)::numeric, 2)::FLOAT as average_rating,
        COUNT(*)::INTEGER as total_ratings,
        json_build_object(
            '1_star', COUNT(*) FILTER (WHERE rating >= 1 AND rating < 2),
            '2_star', COUNT(*) FILTER (WHERE rating >= 2 AND rating < 3),
            '3_star', COUNT(*) FILTER (WHERE rating >= 3 AND rating < 4),
            '4_star', COUNT(*) FILTER (WHERE rating >= 4 AND rating < 5),
            '5_star', COUNT(*) FILTER (WHERE rating = 5)
        ) as rating_distribution
    FROM rates 
    WHERE rates.service_id = p_service_id;
END;
$$ LANGUAGE plpgsql;

-- Create function to get top rated services
CREATE OR REPLACE FUNCTION get_top_rated_services(limit_count INTEGER DEFAULT 10)
RETURNS TABLE(
    service_id INTEGER,
    service_name VARCHAR,
    average_rating FLOAT,
    total_ratings INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.name,
        ROUND(AVG(r.rating)::numeric, 2)::FLOAT as avg_rating,
        COUNT(r.id)::INTEGER as total_count
    FROM services s
    INNER JOIN rates r ON s.id = r.service_id
    WHERE s.is_active = TRUE
    GROUP BY s.id, s.name
    HAVING COUNT(r.id) >= 3  -- Minimum 3 ratings to be considered
    ORDER BY avg_rating DESC, total_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Create tables for the QoE Application
-- Services table to store available services
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    smart_contract_id VARCHAR(255) NOT NULL,
    link_cost DECIMAL(10, 4) NOT NULL,
    callback_wallet_addresses TEXT NOT NULL,
    input_parameters JSONB,
    knowledge_asset JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge table for ML knowledge assets
CREATE TABLE IF NOT EXISTS knowledge (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- Predictors table for ML predictors
CREATE TABLE IF NOT EXISTS predictors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    framework VARCHAR(255) NOT NULL,
    scores JSONB,
    knowledge_id INTEGER REFERENCES knowledge(id) NOT NULL
);

-- Sensors table for sensor information
CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,
    lat DECIMAL(10, 6) NOT NULL,
    lon DECIMAL(10, 6) NOT NULL,
    rate_of_sampling DECIMAL(10, 4) NOT NULL,
    raw_data_id INTEGER NOT NULL,
    unit VARCHAR(50) NOT NULL
);

-- Sensor data table for sensor readings
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER REFERENCES sensors(id) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW() NOT NULL,
    value DECIMAL(15, 6) NOT NULL
);

-- Rates table to store service ratings with encrypted wallet addresses
CREATE TABLE IF NOT EXISTS rates (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    encrypted_wallet TEXT NOT NULL,
    rating DECIMAL(3, 2) CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_services_name ON services(name);
CREATE INDEX IF NOT EXISTS idx_services_active ON services(is_active);

CREATE INDEX IF NOT EXISTS idx_rates_service_encrypted_wallet 
ON rates(service_id, encrypted_wallet);
CREATE INDEX IF NOT EXISTS idx_rates_service_rating 
ON rates(service_id, rating);

CREATE INDEX IF NOT EXISTS idx_sensors_location ON sensors(lat, lon);
CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor_timestamp 
ON sensor_data(sensor_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_predictors_knowledge_id ON predictors(knowledge_id);

-- Insert some sample data if tables are empty (optional)
-- This will only run if no services exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM services LIMIT 1) THEN
        INSERT INTO services (name, description, smart_contract_id, link_cost, callback_wallet_addresses, is_active) VALUES
        ('Weather Data Service', 'Provides weather data Current, Forecasts and Historical for all services', 'weather_contract_001', 0.1, '0x1234567890abcdef1234567890abcdef12345678', TRUE),
        ('Environmental Data', 'Copernicus CDS data inerface', 'service_002', 0.15, '0xabcdef1234567890abcdef1234567890abcdef12', TRUE);
        
        RAISE NOTICE 'Sample services inserted successfully';
    END IF;
END $$;
