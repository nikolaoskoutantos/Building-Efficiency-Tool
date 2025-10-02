# Database Migration for HVAC Location-Based Models
# Run this SQL to update your existing database

# Add new columns to predictors table
ALTER TABLE predictors 
ADD COLUMN IF NOT EXISTS latitude FLOAT NULL,
ADD COLUMN IF NOT EXISTS longitude FLOAT NULL,
ADD COLUMN IF NOT EXISTS model_type VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS model_data JSONB NULL,
ADD COLUMN IF NOT EXISTS training_data_hash VARCHAR(32) NULL,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

# Create training_history table
CREATE TABLE IF NOT EXISTS training_history (
    id SERIAL PRIMARY KEY,
    predictor_id INTEGER REFERENCES predictors(id),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    training_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_completed_at TIMESTAMP NULL,
    training_status VARCHAR(20) NOT NULL,
    training_metrics JSONB NULL,
    data_size INTEGER NULL,
    model_parameters JSONB NULL,
    notes TEXT NULL
);

# Create indexes for efficient location-based queries (safe to run multiple times)
CREATE INDEX IF NOT EXISTS idx_predictors_location ON predictors(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_predictors_model_type ON predictors(model_type);
CREATE INDEX IF NOT EXISTS idx_training_history_location ON training_history(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_training_history_status ON training_history(training_status);

# Create trigger function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

# Create trigger for predictors table (safe to run multiple times)
DROP TRIGGER IF EXISTS update_predictors_updated_at ON predictors;
CREATE TRIGGER update_predictors_updated_at
    BEFORE UPDATE ON predictors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

