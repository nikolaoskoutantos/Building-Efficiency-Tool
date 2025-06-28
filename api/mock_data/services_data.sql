-- Services Initial Data - SQL INSERT statements for populating the services table
-- File: services_data.sql
-- 
-- This file contains INSERT statements to populate the services table with initial data
-- Run this file against your SQLite database to add sample services
--
-- Usage: 
-- sqlite3 dev.db < services_data.sql
-- or execute these statements through your SQLite client

-- Insert sample services into the services table
INSERT INTO services (
    name, 
    description, 
    smart_contract_id, 
    link_cost, 
    callback_wallet_addresses, 
    input_parameters, 
    knowledge_asset
) VALUES 
-- Weather Monitoring Service
(
    'Weather Data Service',
    'Real-time weather data collection and analysis service',
    '0x1234567890abcdef1234567890abcdef12345678',
    0.01,
    '0xabcdef1234567890abcdef1234567890abcdef12',
    '{"location": {"type": "string", "required": true}, "metrics": {"type": "array", "default": ["temperature", "humidity", "pressure"]}, "interval": {"type": "integer", "default": 3600}}',
    '{"data_source": "openweather_api", "accuracy": "high", "update_frequency": "hourly", "coverage": "global"}'
),

-- IoT Sensor Service
(
    'IoT Sensor Network',
    'IoT sensor data collection and monitoring service',
    '0x2345678901bcdef12345678901bcdef123456789',
    0.005,
    '0xbcdef12345678901bcdef12345678901bcdef123',
    '{"sensor_id": {"type": "string", "required": true}, "data_type": {"type": "string", "required": true}, "frequency": {"type": "integer", "default": 60}, "threshold": {"type": "float", "default": 0.0}}',
    '{"protocol": "mqtt", "encryption": "tls", "data_format": "json", "storage": "time_series"}'
),

-- AI Prediction Service
(
    'AI Prediction Engine',
    'Machine learning prediction service for various data types',
    '0x3456789012cdef123456789012cdef1234567890',
    0.02,
    '0xcdef123456789012cdef123456789012cdef1234',
    '{"model_type": {"type": "string", "required": true}, "input_data": {"type": "object", "required": true}, "confidence_threshold": {"type": "float", "default": 0.8}, "prediction_horizon": {"type": "integer", "default": 24}}',
    '{"framework": "tensorflow", "model_version": "2.1", "accuracy": 0.92, "training_data": "historical_sensor_data"}'
),

-- Quality Rating Service
(
    'Quality Rating System',
    'Service quality assessment and rating system',
    '0x4567890123def1234567890123def12345678901',
    0.001,
    '0xdef1234567890123def1234567890123def12345',
    '{"service_id": {"type": "integer", "required": true}, "rating": {"type": "float", "required": true, "min": 1.0, "max": 5.0}, "feedback": {"type": "string", "required": false}, "user_id": {"type": "string", "required": true}}',
    '{"algorithm": "weighted_average", "factors": ["performance", "reliability", "accuracy", "user_satisfaction"], "weight_decay": 0.95}'
),

-- Environmental Monitoring
(
    'Environmental Monitor',
    'Comprehensive environmental data monitoring and analysis',
    '0x567890124ef12345678901234ef123456789012',
    0.008,
    '0xef12345678901234ef12345678901234ef123456',
    '{"location": {"type": "string", "required": true}, "pollutants": {"type": "array", "default": ["pm2.5", "pm10", "o3", "no2", "co"]}, "alert_threshold": {"type": "object", "default": {}}}',
    '{"sensors": ["particle_counter", "gas_analyzer", "weather_station"], "calibration": "auto", "data_quality": "research_grade"}'
),

-- Energy Management Service
(
    'Smart Energy Manager',
    'Intelligent energy consumption monitoring and optimization',
    '0x67890125ef123456789012345ef1234567890123',
    0.007,
    '0xf123456789012345ef123456789012345ef12345',
    '{"building_id": {"type": "string", "required": true}, "devices": {"type": "array", "required": true}, "optimization_target": {"type": "string", "default": "cost"}, "schedule": {"type": "object", "default": {}}}',
    '{"protocol": "zigbee", "ai_optimization": true, "energy_prediction": true, "cost_savings": "up_to_30_percent"}'
),

-- Blockchain Oracle Service
(
    'Blockchain Oracle',
    'Decentralized oracle service for external data integration',
    '0x7890123456f1234567890123456f12345678901234',
    0.015,
    '0x123456789012345f123456789012345f123456789',
    '{"data_source": {"type": "string", "required": true}, "update_frequency": {"type": "integer", "default": 300}, "aggregation_method": {"type": "string", "default": "median"}, "validation_nodes": {"type": "integer", "default": 5}}',
    '{"consensus_mechanism": "proof_of_stake", "data_feeds": ["price", "weather", "iot"], "decentralization_level": "high"}'
),

-- Health Monitoring Service
(
    'Health Data Monitor',
    'Personal and environmental health monitoring service',
    '0x890123456f12345678901234567f123456789012345',
    0.012,
    '0x23456789012345f123456789012345f1234567890',
    '{"patient_id": {"type": "string", "required": true}, "vital_signs": {"type": "array", "required": true}, "alert_contacts": {"type": "array", "default": []}, "emergency_threshold": {"type": "object", "required": true}}',
    '{"compliance": "hipaa", "encryption": "end_to_end", "ai_analysis": true, "emergency_response": "automated"}'
),

-- Supply Chain Tracker
(
    'Supply Chain Tracker',
    'End-to-end supply chain visibility and tracking service',
    '0x90123456f123456789012345678f1234567890123456',
    0.006,
    '0x3456789012345f123456789012345f12345678901',
    '{"product_id": {"type": "string", "required": true}, "tracking_points": {"type": "array", "required": true}, "compliance_checks": {"type": "array", "default": []}, "stakeholder_access": {"type": "object", "default": {}}}',
    '{"blockchain_ledger": true, "rfid_integration": true, "compliance_standards": ["iso", "gmp", "fda"], "transparency_level": "full"}'
),

-- Agricultural Monitoring
(
    'AgriTech Monitor',
    'Precision agriculture monitoring and optimization service',
    '0xa0123456f1234567890123456789f1234567890123456',
    0.009,
    '0x456789012345f123456789012345f123456789012',
    '{"farm_id": {"type": "string", "required": true}, "crop_type": {"type": "string", "required": true}, "monitoring_params": {"type": "array", "default": ["soil_moisture", "temperature", "ph", "nutrients"]}, "irrigation_control": {"type": "boolean", "default": false}}',
    '{"sensors": ["soil", "weather", "drone", "satellite"], "ai_recommendations": true, "yield_prediction": true, "sustainability_metrics": true}'
);

-- Optional: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_services_name ON services(name);
CREATE INDEX IF NOT EXISTS idx_services_smart_contract ON services(smart_contract_id);
CREATE INDEX IF NOT EXISTS idx_services_link_cost ON services(link_cost);

-- Optional: Query to verify the data was inserted correctly
-- SELECT COUNT(*) as total_services FROM services;
-- SELECT name, smart_contract_id, link_cost FROM services ORDER BY name;
