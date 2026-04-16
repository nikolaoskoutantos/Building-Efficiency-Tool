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
interval_cte AS (
  SELECT interval '5 minutes' AS step
),
time_series AS (
  SELECT generate_series(in_start_time, in_end_time, (SELECT step FROM interval_cte))::timestamp AS ts
),
bld AS (
    SELECT b.*
    FROM public.buildings b
    WHERE b.id = in_building_id
),
weather_location AS (
    SELECT wc.lat, wc.lon
    FROM (
        SELECT DISTINCT wd.lat, wd.lon
        FROM public.weather_data wd
    ) wc
    CROSS JOIN bld b
    ORDER BY abs(wc.lat - (b.lat::float8)) + abs(wc.lon - (b.lon::float8))
    LIMIT 1
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
       ON EXISTS (
            SELECT 1
            FROM weather_location wl
            WHERE wl.lat = w.lat
              AND wl.lon = w.lon
       )
      AND w."timestamp" = ts.ts
LEFT JOIN public.hvac_schedule_intervals hi
       ON hi.building_id = b.id
      AND hi.hvac_unit_id = s.hvac_unit_id
      AND ts.ts >= (hi.start_ts AT TIME ZONE 'UTC')::timestamp
      AND ts.ts <  (hi.end_ts   AT TIME ZONE 'UTC')::timestamp
ORDER BY ts.ts, s.id;
$$;




CREATE OR REPLACE FUNCTION public.aggregate_sensor_data_5m(p_from timestamptz, p_to timestamptz)
RETURNS void
LANGUAGE sql
AS $$
WITH interval_cte AS (
  SELECT interval '5 minutes' AS step
)
INSERT INTO public.sensor_data (sensor_id, "timestamp", value, measurement_type, unit)
SELECT
  r.sensor_id,
  date_bin((SELECT step FROM interval_cte), r."timestamp", timestamptz '1970-01-01 00:00:00+00') AS bucket_start,
  avg(r.value)::double precision AS value,
  r.measurement_type,
  max(r.unit) AS unit
FROM public.sensor_data_raw r
WHERE r."timestamp" >= p_from
  AND r."timestamp" <  p_to
  AND r.value IS NOT NULL
GROUP BY r.sensor_id, r.measurement_type, bucket_start
ON CONFLICT (sensor_id, measurement_type, "timestamp")
DO UPDATE SET
  value = EXCLUDED.value,
  unit  = EXCLUDED.unit;
$$;

CREATE OR REPLACE FUNCTION public.run_aggregate_sensor_data_5m()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM public.aggregate_sensor_data_5m(now() - interval '15 minutes', now());
END;
$$;

-- Dashboard time grid function: 5h past + 3h future, 5-min intervals
CREATE OR REPLACE FUNCTION public.dashboard_time_grid(
    in_building_id INTEGER,
    in_ref_now TIMESTAMPTZ DEFAULT now(),
    in_past_range INTERVAL DEFAULT interval '5 hours',
    in_future_range INTERVAL DEFAULT interval '3 hours'
)
RETURNS TABLE(
    ts timestamptz,
    temperature double precision,
    presence double precision,
    energy double precision,
    outdoor_temperature double precision,
    outdoor_humidity double precision,
    outdoor_pressure double precision,
    wind_speed double precision,
    wind_direction double precision,
    precipitation double precision,
    weather_description character varying,
    weather_source_timestamp timestamptz,
    hvac_is_on boolean,
    hvac_setpoint double precision,
    active_hvac_intervals integer,
    optimization_time timestamptz,
    input_hash text,
    output_hash text,
    energy_saving_kwh double precision,
    baseline_consumption_kwh double precision,
    optimized_consumption_kwh double precision,
    environmental_points double precision,
    notes text,
    is_optimized boolean
) AS $$
WITH params AS (
    SELECT
        in_building_id AS building_id,
        date_bin(interval '5 minutes', in_ref_now, timestamptz '1970-01-01 00:00:00+00') AS ref_now,
        in_past_range AS past_range,
        in_future_range AS future_range
),
building AS (
    SELECT
        b.id,
        b.lat::float8 AS lat,
        b.lon::float8 AS lon
    FROM public.buildings b
    JOIN params p ON p.building_id = b.id
    WHERE b.lat IS NOT NULL
      AND b.lon IS NOT NULL
),
weather_location AS (
    SELECT wc.lat, wc.lon
    FROM (
        SELECT DISTINCT wd.lat, wd.lon
        FROM public.weather_data wd
    ) wc
    CROSS JOIN building b
    ORDER BY abs(wc.lat - b.lat) + abs(wc.lon - b.lon)
    LIMIT 1
),
grid AS (
    SELECT DISTINCT ts
    FROM (
        SELECT
            date_bin(
                interval '5 minutes',
                sd.timestamp,
                timestamptz '1970-01-01 00:00:00+00'
            ) AS ts
        FROM public.sensor_data sd
        JOIN public.sensors s ON s.id = sd.sensor_id
        JOIN params p ON s.building_id = p.building_id
        WHERE sd.timestamp >= p.ref_now - p.past_range
          AND sd.timestamp <= p.ref_now

        UNION

        SELECT generate_series(
            p.ref_now + interval '5 minutes',
            p.ref_now + p.future_range,
            interval '5 minutes'
        ) AS ts
        FROM params p
    ) timeline
),
sensors AS (
    SELECT
        s.id,
        lower(s.type) AS type
    FROM public.sensors s
    JOIN params p ON s.building_id = p.building_id
),
sensor_values AS (
    SELECT
        g.ts,
        s.type,
        sd.value
    FROM grid g
    CROSS JOIN sensors s
    LEFT JOIN LATERAL (
        SELECT sd.value
        FROM public.sensor_data sd
        WHERE sd.sensor_id = s.id
          AND sd.timestamp <= g.ts
        ORDER BY sd.timestamp DESC
        LIMIT 1
    ) sd ON true
),
weather_values AS (
    SELECT
        g.ts,
        w.temperature AS outdoor_temperature,
        w.humidity AS outdoor_humidity,
        w.pressure AS outdoor_pressure,
        w.wind_speed,
        w.wind_direction,
        w.precipitation,
        w.weather_description,
        w.timestamp AS weather_source_timestamp
    FROM grid g
    CROSS JOIN building b
    LEFT JOIN LATERAL (
        SELECT
            wd.temperature,
            wd.humidity,
            wd.pressure,
            wd.wind_speed,
            wd.wind_direction,
            wd.precipitation,
            wd.weather_description,
            wd.timestamp
        FROM public.weather_data wd
        WHERE EXISTS (
                SELECT 1
                FROM weather_location wl
                WHERE wl.lat = wd.lat
                  AND wl.lon = wd.lon
        )
          AND wd.timestamp <= g.ts
        ORDER BY wd.timestamp DESC
        LIMIT 1
    ) w ON true
),
hvac_values AS (
    SELECT
        g.ts,
        COALESCE(bool_or(hi.is_on), false) AS hvac_is_on,
        max(hi.setpoint) FILTER (WHERE hi.is_on) AS hvac_setpoint,
        count(*) FILTER (WHERE hi.is_on) AS active_hvac_intervals
    FROM grid g
    CROSS JOIN params p
    LEFT JOIN public.hvac_schedule_intervals hi
      ON hi.building_id = p.building_id
     AND g.ts >= hi.start_ts
     AND g.ts < hi.end_ts
    GROUP BY g.ts
),
energy_values AS (
    SELECT
        g.ts,
        o.optimization_time,
        o.input_hash,
        o.output_hash,
        o.energy_saving_kwh,
        o.baseline_consumption_kwh,
        o.optimized_consumption_kwh,
        o.environmental_points,
        o.notes,
        o.is_optimized
    FROM grid g
    CROSS JOIN params p
    LEFT JOIN LATERAL (
        SELECT
            o.optimization_time,
            o.input_hash,
            o.output_hash,
            o.energy_saving_kwh,
            o.baseline_consumption_kwh,
            o.optimized_consumption_kwh,
            o.environmental_points,
            o.notes,
            o.is_optimized
        FROM public.optimization_results o
        WHERE o.building_id = p.building_id
          AND o.optimization_time <= g.ts
        ORDER BY o.optimization_time DESC
        LIMIT 1
    ) o ON true
)
SELECT
    g.ts,
    MAX(CASE WHEN sv.type = 'temperature' THEN sv.value END) AS temperature,
    MAX(CASE WHEN sv.type = 'presence' THEN sv.value END) AS presence,
    MAX(CASE WHEN sv.type = 'energy' THEN sv.value END) AS energy,
    wv.outdoor_temperature,
    wv.outdoor_humidity,
    wv.outdoor_pressure,
    wv.wind_speed,
    wv.wind_direction,
    wv.precipitation,
    wv.weather_description,
    wv.weather_source_timestamp,
    hv.hvac_is_on,
    hv.hvac_setpoint,
    hv.active_hvac_intervals,
    ev.optimization_time,
    ev.input_hash,
    ev.output_hash,
    ev.energy_saving_kwh,
    ev.baseline_consumption_kwh,
    ev.optimized_consumption_kwh,
    ev.environmental_points,
    ev.notes,
    ev.is_optimized
FROM grid g
LEFT JOIN sensor_values sv ON sv.ts = g.ts
LEFT JOIN weather_values wv ON wv.ts = g.ts
LEFT JOIN hvac_values hv ON hv.ts = g.ts
LEFT JOIN energy_values ev ON ev.ts = g.ts
GROUP BY
    g.ts,
    wv.outdoor_temperature,
    wv.outdoor_humidity,
    wv.outdoor_pressure,
    wv.wind_speed,
    wv.wind_direction,
    wv.precipitation,
    wv.weather_description,
    wv.weather_source_timestamp,
    hv.hvac_is_on,
    hv.hvac_setpoint,
    hv.active_hvac_intervals,
    ev.optimization_time,
    ev.input_hash,
    ev.output_hash,
    ev.energy_saving_kwh,
    ev.baseline_consumption_kwh,
    ev.optimized_consumption_kwh,
    ev.environmental_points,
    ev.notes,
    ev.is_optimized
ORDER BY g.ts;
$$ LANGUAGE sql;


-- Efficiency tool function: measured history + forecast future, both on 5-minute buckets.
CREATE OR REPLACE FUNCTION public.efficiency_tool_timeseries(
    in_building_id INTEGER,
    in_ref_now TIMESTAMPTZ DEFAULT now(),
    in_past_range INTERVAL DEFAULT interval '5 hours',
    in_future_range INTERVAL DEFAULT interval '3 hours'
)
RETURNS TABLE(
    ts timestamptz,
    data_kind text,
    temperature double precision,
    presence double precision,
    energy double precision,
    outdoor_temperature double precision,
    outdoor_humidity double precision,
    outdoor_pressure double precision,
    wind_speed double precision,
    wind_direction double precision,
    precipitation double precision,
    weather_description character varying,
    weather_source_timestamp timestamptz,
    hvac_is_on boolean,
    hvac_setpoint double precision,
    active_hvac_intervals integer,
    optimization_time timestamptz,
    input_hash text,
    output_hash text,
    energy_saving_kwh double precision,
    baseline_consumption_kwh double precision,
    optimized_consumption_kwh double precision,
    environmental_points double precision,
    notes text,
    is_optimized boolean
)
LANGUAGE sql
AS $$
WITH params AS (
    SELECT
        in_building_id AS building_id,
        date_bin(interval '5 minutes', in_ref_now, timestamptz '1970-01-01 00:00:00+00') AS ref_now,
        in_past_range AS past_range,
        in_future_range AS future_range
),
building AS (
    SELECT
        b.id,
        b.lat::float8 AS lat,
        b.lon::float8 AS lon
    FROM public.buildings b
    JOIN params p ON p.building_id = b.id
),
weather_location AS (
    SELECT wc.lat, wc.lon
    FROM (
        SELECT DISTINCT wd.lat, wd.lon
        FROM public.weather_data wd
    ) wc
    CROSS JOIN building b
    ORDER BY abs(wc.lat - b.lat) + abs(wc.lon - b.lon)
    LIMIT 1
),
history_rows AS (
    SELECT
        gsw.sensor_timestamp::timestamptz AS ts,
        'history'::text AS data_kind,
        MAX(CASE WHEN lower(gsw.sensor_type) = 'temperature' THEN gsw.sensor_value END) AS temperature,
        MAX(CASE WHEN lower(gsw.sensor_type) = 'presence' THEN gsw.sensor_value END) AS presence,
        MAX(CASE WHEN lower(gsw.sensor_type) = 'energy' THEN gsw.sensor_value END) AS energy,
        MAX(gsw.temperature) AS outdoor_temperature,
        MAX(gsw.humidity) AS outdoor_humidity,
        MAX(gsw.pressure) AS outdoor_pressure,
        MAX(gsw.wind_speed) AS wind_speed,
        MAX(gsw.wind_direction) AS wind_direction,
        MAX(gsw.precipitation) AS precipitation,
        MAX(gsw.weather_description) AS weather_description,
        MAX(gsw.weather_timestamp)::timestamptz AS weather_source_timestamp,
        COALESCE(bool_or(gsw.hvac_is_on), false) AS hvac_is_on,
        MAX(gsw.hvac_setpoint) FILTER (WHERE gsw.hvac_is_on) AS hvac_setpoint,
        count(*) FILTER (WHERE gsw.hvac_is_on) AS active_hvac_intervals
    FROM params p
    CROSS JOIN LATERAL public.get_building_sensor_weather(
        p.building_id,
        (p.ref_now - p.past_range)::timestamp,
        p.ref_now::timestamp
    ) gsw
    GROUP BY gsw.sensor_timestamp
),
forecast_grid AS (
    SELECT generate_series(
        p.ref_now + interval '5 minutes',
        p.ref_now + p.future_range,
        interval '5 minutes'
    ) AS ts
    FROM params p
),
forecast_weather AS (
    SELECT
        fg.ts,
        'forecast'::text AS data_kind,
        NULL::double precision AS temperature,
        NULL::double precision AS presence,
        NULL::double precision AS energy,
        wd.temperature AS outdoor_temperature,
        wd.humidity AS outdoor_humidity,
        wd.pressure AS outdoor_pressure,
        wd.wind_speed,
        wd.wind_direction,
        wd.precipitation,
        wd.weather_description,
        wd.timestamp AS weather_source_timestamp
    FROM forecast_grid fg
    LEFT JOIN public.weather_data wd
      ON EXISTS (
            SELECT 1
            FROM weather_location wl
            WHERE wl.lat = wd.lat
              AND wl.lon = wd.lon
      )
     AND wd.timestamp = fg.ts
),
forecast_context AS (
    SELECT
        fw.ts,
        fw.data_kind,
        fw.temperature,
        fw.presence,
        fw.energy,
        fw.outdoor_temperature,
        fw.outdoor_humidity,
        fw.outdoor_pressure,
        fw.wind_speed,
        fw.wind_direction,
        fw.precipitation,
        fw.weather_description,
        fw.weather_source_timestamp,
        COALESCE(bool_or(hi.is_on), false) AS hvac_is_on,
        max(hi.setpoint) FILTER (WHERE hi.is_on) AS hvac_setpoint,
        count(*) FILTER (WHERE hi.is_on) AS active_hvac_intervals,
        opt.optimization_time,
        opt.input_hash,
        opt.output_hash,
        opt.energy_saving_kwh,
        opt.baseline_consumption_kwh,
        opt.optimized_consumption_kwh,
        opt.environmental_points,
        opt.notes,
        opt.is_optimized
    FROM forecast_weather fw
    CROSS JOIN params p
    LEFT JOIN public.hvac_schedule_intervals hi
      ON hi.building_id = p.building_id
     AND fw.ts >= hi.start_ts
     AND fw.ts < hi.end_ts
    LEFT JOIN LATERAL (
        SELECT
            o.optimization_time,
            o.input_hash,
            o.output_hash,
            o.energy_saving_kwh,
            o.baseline_consumption_kwh,
            o.optimized_consumption_kwh,
            o.environmental_points,
            o.notes,
            o.is_optimized
        FROM public.optimization_results o
        WHERE o.building_id = p.building_id
          AND o.optimization_time <= fw.ts
        ORDER BY o.optimization_time DESC
        LIMIT 1
    ) opt ON true
    GROUP BY
        fw.ts,
        fw.data_kind,
        fw.temperature,
        fw.presence,
        fw.energy,
        fw.outdoor_temperature,
        fw.outdoor_humidity,
        fw.outdoor_pressure,
        fw.wind_speed,
        fw.wind_direction,
        fw.precipitation,
        fw.weather_description,
        fw.weather_source_timestamp,
        opt.optimization_time,
        opt.input_hash,
        opt.output_hash,
        opt.energy_saving_kwh,
        opt.baseline_consumption_kwh,
        opt.optimized_consumption_kwh,
        opt.environmental_points,
        opt.notes,
        opt.is_optimized
)
SELECT
    h.ts,
    h.data_kind,
    h.temperature,
    h.presence,
    h.energy,
    h.outdoor_temperature,
    h.outdoor_humidity,
    h.outdoor_pressure,
    h.wind_speed,
    h.wind_direction,
    h.precipitation,
    h.weather_description,
    h.weather_source_timestamp,
    h.hvac_is_on,
    h.hvac_setpoint,
    h.active_hvac_intervals,
    opt.optimization_time,
    opt.input_hash,
    opt.output_hash,
    opt.energy_saving_kwh,
    opt.baseline_consumption_kwh,
    opt.optimized_consumption_kwh,
    opt.environmental_points,
    opt.notes,
    opt.is_optimized
FROM history_rows h
LEFT JOIN params p ON true
LEFT JOIN LATERAL (
    SELECT
        o.optimization_time,
        o.input_hash,
        o.output_hash,
        o.energy_saving_kwh,
        o.baseline_consumption_kwh,
        o.optimized_consumption_kwh,
        o.environmental_points,
        o.notes,
        o.is_optimized
    FROM public.optimization_results o
    WHERE o.building_id = p.building_id
      AND o.optimization_time <= h.ts
    ORDER BY o.optimization_time DESC
    LIMIT 1
) opt ON true

UNION ALL

SELECT
    fc.ts,
    fc.data_kind,
    fc.temperature,
    fc.presence,
    fc.energy,
    fc.outdoor_temperature,
    fc.outdoor_humidity,
    fc.outdoor_pressure,
    fc.wind_speed,
    fc.wind_direction,
    fc.precipitation,
    fc.weather_description,
    fc.weather_source_timestamp,
    fc.hvac_is_on,
    fc.hvac_setpoint,
    fc.active_hvac_intervals,
    fc.optimization_time,
    fc.input_hash,
    fc.output_hash,
    fc.energy_saving_kwh,
    fc.baseline_consumption_kwh,
    fc.optimized_consumption_kwh,
    fc.environmental_points,
    fc.notes,
    fc.is_optimized
FROM forecast_context fc
ORDER BY ts;
$$;


