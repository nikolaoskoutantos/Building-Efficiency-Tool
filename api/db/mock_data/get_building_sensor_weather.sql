CREATE OR REPLACE FUNCTION get_building_sensor_weather(
    in_building_id INTEGER,
    in_start_time TIMESTAMP,
    in_end_time TIMESTAMP
)
RETURNS TABLE(
    sensor_id INTEGER,
    sensor_type VARCHAR,
    sensor_value FLOAT,
    sensor_timestamp TIMESTAMP,
    measurement_type VARCHAR,
    sensor_unit VARCHAR,
    weather_timestamp TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    precipitation FLOAT,
    weather_description VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sd.sensor_id,
        s.type,
        sd.value,
        sd.timestamp,
        sd.measurement_type,
        sd.unit,
        w.timestamp,
        w.temperature,
        w.humidity,
        w.pressure,
        w.wind_speed,
        w.wind_direction,
        w.precipitation,
        w.weather_description
    FROM sensors s
    JOIN sensor_data sd ON s.id = sd.sensor_id
    JOIN buildings b ON s.building_id = b.id
    LEFT JOIN weather_data w
        ON w.lat = b.lat::float
        AND w.lon = b.lon::float
        AND w.timestamp BETWEEN in_start_time AND in_end_time
    WHERE
        b.id = in_building_id
        AND sd.timestamp BETWEEN in_start_time AND in_end_time
    ORDER BY sd.timestamp ASC, sd.sensor_id ASC;
END;
$$ LANGUAGE plpgsql;