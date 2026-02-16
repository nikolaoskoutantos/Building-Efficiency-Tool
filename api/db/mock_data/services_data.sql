-- Services Initial Data - PostgreSQL INSERT statements for populating the services table
-- File: services_data.sql
-- 
-- This file contains INSERT statements to populate the services table with initial data
-- Compatible with PostgreSQL database
--
-- Usage: Execute through psycopg2 or psql

-- Insert sample services into the services table (PostgreSQL compatible)
INSERT INTO services (
    name, 
    description, 
    smart_contract_id, 
    link_cost, 
    callback_wallet_addresses, 
    input_parameters, 
    knowledge_asset,
    is_active,
    created_at,
    updated_at
) VALUES 
-- Weather Monitoring Service
(
    'Weather Data Service',
    'Real-time weather data collection and analysis service',
    '0x1234567890abcdef1234567890abcdef12345678',
    0.01,
    '0xabcdef1234567890abcdef1234567890abcdef12',
    '{"location": {"type": "string", "required": true}, "metrics": {"type": "array", "default": ["temperature", "humidity", "pressure"]}, "interval": {"type": "integer", "default": 3600}}'::jsonb,
    '{"data_source": "openweather_api", "accuracy": "high", "update_frequency": "hourly", "coverage": "global"}'::jsonb,
    1,
    NOW(),
    NOW()
),

-- IoT Sensor Service
(
    'IoT Sensor Network',
    'IoT sensor data collection and monitoring service',
    '0x2345678901bcdef12345678901bcdef123456789',
    0.005,
    '0xbcdef12345678901bcdef12345678901bcdef123',
    '{"sensor_id": {"type": "string", "required": true}, "data_type": {"type": "string", "required": true}, "frequency": {"type": "integer", "default": 60}, "threshold": {"type": "float", "default": 0.0}}'::jsonb,
    '{"protocol": "mqtt", "encryption": "tls", "data_format": "json", "storage": "time_series"}'::jsonb,
    1,
    NOW(),
    NOW()
),

-- Optional: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_services_name ON services(name);
CREATE INDEX IF NOT EXISTS idx_services_smart_contract ON services(smart_contract_id);
CREATE INDEX IF NOT EXISTS idx_services_link_cost ON services(link_cost);

-- Optional: Query to verify the data was inserted correctly
-- SELECT COUNT(*) as total_services FROM services;
-- SELECT name, smart_contract_id, link_cost FROM services ORDER BY name;
