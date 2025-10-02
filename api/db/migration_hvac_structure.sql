-- Migration for buildings, sensors, hvac_schedules, and predictors relations

-- 1. Create buildings table
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT
);

-- 2. Alter sensors table: add building_id, hvac_id, type
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS building_id INTEGER REFERENCES buildings(id);
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS hvac_id INTEGER REFERENCES sensors(id);
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS type VARCHAR(50);

-- 3. Create hvac_schedules table
CREATE TABLE IF NOT EXISTS hvac_schedules (
    id SERIAL PRIMARY KEY,
    hvac_id INTEGER NOT NULL REFERENCES sensors(id),
    periods JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Alter predictors table: add hvac_schedule_id
ALTER TABLE predictors ADD COLUMN IF NOT EXISTS hvac_schedule_id INTEGER REFERENCES hvac_schedules(id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sensors_building_id ON sensors(building_id);
CREATE INDEX IF NOT EXISTS idx_sensors_hvac_id ON sensors(hvac_id);
CREATE INDEX IF NOT EXISTS idx_sensors_type ON sensors(type);
CREATE INDEX IF NOT EXISTS idx_hvac_schedules_hvac_id ON hvac_schedules(hvac_id);
CREATE INDEX IF NOT EXISTS idx_predictors_hvac_schedule_id ON predictors(hvac_schedule_id);
