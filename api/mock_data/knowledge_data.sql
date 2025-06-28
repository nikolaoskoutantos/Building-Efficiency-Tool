-- Knowledge Base Initial Data - SQL INSERT statements for populating the knowledge table
-- File: knowledge_data.sql
-- 
-- This file contains INSERT statements to populate the knowledge table with initial data

-- Insert sample knowledge assets into the knowledge table
INSERT INTO knowledge (
    name, 
    description
) VALUES 
(
    'Weather Analysis Knowledge Base',
    'Comprehensive weather data analysis and prediction algorithms'
),
(
    'IoT Sensor Data Processing',
    'Knowledge base for processing and analyzing IoT sensor data streams'
),
(
    'Machine Learning Models Repository',
    'Collection of trained ML models for various prediction tasks'
),
(
    'Environmental Monitoring Expertise',
    'Knowledge assets for environmental data interpretation and analysis'
),
(
    'Energy Optimization Algorithms',
    'Smart algorithms for energy consumption optimization and management'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_knowledge_name ON knowledge(name);
