CREATE OR REPLACE FUNCTION public.get_building_sensor_weather(
    in_building_id INTEGER,
    in_start_time  TIMESTAMP,
    in_end_time    TIMESTAMP
)
RETURNS TABLE(
    sensor_id integer,
    sensor_type character varying,
    sensor_value double precision,
    sensor_timestamp timestamp without time zone,
    measurement_type character varying,
    sensor_unit character varying,
    weather_timestamp timestamp without time zone,
    temperature double precision,
    humidity double precision,
    pressure double precision,
    wind_speed double precision,
    wind_direction double precision,
    precipitation double precision,
    weather_description character varying,
    hvac_interval_id integer,
    hvac_is_on boolean,
    hvac_setpoint double precision,
    hvac_interval_start timestamp without time zone,
    hvac_interval_end timestamp without time zone
)
LANGUAGE sql
AS $$
WITH
time_series AS (
    SELECT generate_series(in_start_time, in_end_time, interval '5 minutes')::timestamp AS ts
),
bld AS (
    SELECT b.*
    FROM public.buildings b
    WHERE b.id = in_building_id
),
sensors_for_bld AS (
    SELECT s.*
    FROM public.sensors s
    WHERE s.building_id = in_building_id
),
sd_dedup AS (
    SELECT DISTINCT ON (sd.sensor_id, sd."timestamp", sd.measurement_type)
           sd.sensor_id,
           sd."timestamp",
           sd.measurement_type,
           sd.value,
           sd.unit
    FROM public.sensor_data sd
    WHERE sd."timestamp" >= in_start_time
      AND sd."timestamp" <= in_end_time
    ORDER BY sd.sensor_id, sd."timestamp", sd.measurement_type, sd.id DESC
)
SELECT
    s.id AS sensor_id,
    s."type" AS sensor_type,
    sd.value AS sensor_value,
    ts.ts AS sensor_timestamp,
    sd.measurement_type,
    sd.unit AS sensor_unit,
    w."timestamp" AS weather_timestamp,
    w.temperature,
    w.humidity,
    w.pressure,
    w.wind_speed,
    w.wind_direction,
    w.precipitation,
    w.weather_description,
    hi.id AS hvac_interval_id,
    hi.is_on AS hvac_is_on,
    hi.setpoint AS hvac_setpoint,
    (hi.start_ts AT TIME ZONE 'UTC')::timestamp AS hvac_interval_start,
    (hi.end_ts   AT TIME ZONE 'UTC')::timestamp AS hvac_interval_end
FROM time_series ts
JOIN bld b ON TRUE
CROSS JOIN sensors_for_bld s
LEFT JOIN sd_dedup sd
       ON sd.sensor_id = s.id
      AND sd."timestamp" = ts.ts
LEFT JOIN public.weather_data w
       ON w.lat = (b.lat::float8)
      AND w.lon = (b.lon::float8)
      AND w."timestamp" = ts.ts
LEFT JOIN public.hvac_schedule_intervals hi
       ON hi.building_id = b.id
      AND hi.hvac_unit_id = s.hvac_unit_id
      AND ts.ts >= (hi.start_ts AT TIME ZONE 'UTC')::timestamp
      AND ts.ts <  (hi.end_ts   AT TIME ZONE 'UTC')::timestamp
ORDER BY ts.ts, s.id;
$$;
