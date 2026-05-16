CREATE OR REPLACE FUNCTION public.five_minute_interval()
RETURNS interval
LANGUAGE sql
IMMUTABLE
AS $$
SELECT interval '5 minutes';
$$;

CREATE EXTENSION IF NOT EXISTS pg_cron;

CREATE OR REPLACE FUNCTION public.utc_timezone_name()
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
SELECT 'UTC';
$$;


CREATE OR REPLACE FUNCTION public.unix_epoch_utc()
RETURNS timestamptz
LANGUAGE sql
IMMUTABLE
AS $$
SELECT timestamptz '1970-01-01 00:00:00+00';
$$;


CREATE OR REPLACE FUNCTION public.default_dashboard_past_range()
RETURNS interval
LANGUAGE sql
IMMUTABLE
AS $$
SELECT interval '5 hours';
$$;


CREATE OR REPLACE FUNCTION public.default_dashboard_future_range()
RETURNS interval
LANGUAGE sql
IMMUTABLE
AS $$
SELECT interval '3 hours';
$$;


CREATE OR REPLACE FUNCTION public.temperature_sensor_type()
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
SELECT 'temperature';
$$;


CREATE OR REPLACE FUNCTION public.presence_sensor_type()
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
SELECT 'presence';
$$;


CREATE OR REPLACE FUNCTION public.energy_sensor_type()
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
SELECT 'energy';
$$;


CREATE OR REPLACE FUNCTION public.get_building_sensor_weather(
    in_building_id  INTEGER,
    in_start_time   TIMESTAMP,
    in_end_time     TIMESTAMP,
    in_hvac_unit_id INTEGER DEFAULT NULL
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
  SELECT public.five_minute_interval() AS step
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
    ORDER BY abs(wc.lat - (b.lat::float8)) + abs(wc.lon - (b.lon::float8)) ASC
    LIMIT 1
),
sensors_for_bld AS (
    SELECT s.*
    FROM public.sensors s
    WHERE s.building_id = in_building_id
      AND (in_hvac_unit_id IS NULL OR s.hvac_unit_id = in_hvac_unit_id)
),
sd_dedup AS (
    SELECT DISTINCT ON (sd.sensor_id, sd.ts)
           sd.sensor_id,
           sd.ts,
           sd.value
    FROM public.sensor_data sd
    WHERE sd.ts >= in_start_time
      AND sd.ts <= in_end_time
    ORDER BY sd.sensor_id ASC, sd.ts ASC, sd.id DESC
),
weather_at_ts AS (
    SELECT
        ts.ts,
        w."timestamp" AS weather_timestamp,
        w.temperature,
        w.humidity,
        w.pressure,
        w.wind_speed,
        w.wind_direction,
        w.precipitation,
        w.weather_description
    FROM time_series ts
    LEFT JOIN public.weather_data w
           ON EXISTS (
                SELECT 1
                FROM weather_location wl
                WHERE wl.lat = w.lat
                  AND wl.lon = w.lon
           )
          AND w."timestamp" = ts.ts
)
SELECT
    s.id AS sensor_id,
    s.sensor_type AS sensor_type,
    sd.value AS sensor_value,
    ts.ts AS sensor_timestamp,
    s.sensor_type AS measurement_type,
    s.unit AS sensor_unit,
    (SELECT wat.weather_timestamp FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS weather_timestamp,
    (SELECT wat.temperature FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS temperature,
    (SELECT wat.humidity FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS humidity,
    (SELECT wat.pressure FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS pressure,
    (SELECT wat.wind_speed FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS wind_speed,
    (SELECT wat.wind_direction FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS wind_direction,
    (SELECT wat.precipitation FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS precipitation,
    (SELECT wat.weather_description FROM weather_at_ts wat WHERE wat.ts = ts.ts) AS weather_description,
    hi.id AS hvac_interval_id,
    (hi.hvac_status IS NOT NULL AND hi.hvac_status <> 'off') AS hvac_is_on,
    hi.setpoint_c::double precision AS hvac_setpoint,
    hi.ts::timestamp AS hvac_interval_start,
    NULL::timestamp AS hvac_interval_end
FROM time_series ts
CROSS JOIN sensors_for_bld s
LEFT JOIN sd_dedup sd
       ON sd.sensor_id = s.id
      AND sd.ts = ts.ts
LEFT JOIN LATERAL (
    SELECT zs.id, zs.hvac_status, zs.setpoint_c, zs.ts
    FROM public.zone_states zs
    WHERE zs.hvac_unit_id = s.hvac_unit_id
      AND zs.ts <= ts.ts
    ORDER BY zs.ts DESC
    LIMIT 1
) hi ON true
ORDER BY ts.ts ASC, s.id ASC;
$$;




CREATE OR REPLACE FUNCTION public.aggregate_sensor_data_5m(p_from timestamptz, p_to timestamptz)
RETURNS void
LANGUAGE sql
AS $$
WITH interval_cte AS (
  SELECT public.five_minute_interval() AS step
),
bucketed AS (
  SELECT
    r.sensor_id,
    r.building_id,
    date_bin((SELECT step FROM interval_cte), r.ts, public.unix_epoch_utc()) AS bucket_start,
    lower(coalesce(resolved_unit.aggregation_method, 'mean'))                  AS aggregation_method,
    CASE lower(coalesce(resolved_unit.aggregation_method, 'mean'))
      WHEN 'sum' THEN sum(r.value)::double precision
      WHEN 'min' THEN min(r.value)::double precision
      WHEN 'max' THEN max(r.value)::double precision
      WHEN 'last' THEN (array_agg(r.value ORDER BY r.ts DESC) FILTER (WHERE r.value IS NOT NULL))[1]::double precision
      ELSE avg(r.value)::double precision
    END                                                                       AS agg_value,
    -- text values are always collapsed to the last non-null reading in the bucket
    (array_agg(r.value_text ORDER BY r.ts DESC) FILTER (WHERE r.value_text IS NOT NULL))[1] AS agg_value_text,
    -- boolean aggregation is unit-driven too
    CASE
      WHEN count(r.value_bool) FILTER (WHERE r.value_bool IS NOT NULL) = 0 THEN NULL
      WHEN lower(coalesce(resolved_unit.aggregation_method, 'mean')) = 'max' THEN bool_or(r.value_bool)
      WHEN lower(coalesce(resolved_unit.aggregation_method, 'mean')) = 'min' THEN bool_and(r.value_bool)
      WHEN lower(coalesce(resolved_unit.aggregation_method, 'mean')) = 'last' THEN
        (array_agg(r.value_bool ORDER BY r.ts DESC) FILTER (WHERE r.value_bool IS NOT NULL))[1]
      ELSE (
        (count(*) FILTER (WHERE r.value_bool = true))::float
        / count(r.value_bool) FILTER (WHERE r.value_bool IS NOT NULL) >= 0.5
      )
    END                                                                        AS agg_value_bool
  FROM public.sensor_data_raw r
  JOIN public.sensors s
    ON s.id = r.sensor_id
  LEFT JOIN LATERAL (
    SELECT su.id, su.symbol, su.aggregation_method
    FROM public.sensor_units su
    WHERE su.id = s.unit_id
       OR (
         s.unit_id IS NULL
         AND (
           su.symbol = s.unit
           OR lower(su.symbol) = regexp_replace(lower(btrim(s.unit)), '[\s_-]+', '_', 'g')
           OR su.aliases @> to_jsonb(ARRAY[regexp_replace(lower(btrim(s.unit)), '[\s_-]+', '_', 'g')])
         )
       )
    ORDER BY CASE
      WHEN su.id = s.unit_id THEN 0
      WHEN su.symbol = s.unit THEN 1
      WHEN lower(su.symbol) = regexp_replace(lower(btrim(s.unit)), '[\s_-]+', '_', 'g') THEN 2
      ELSE 3
    END
    LIMIT 1
  ) resolved_unit
    ON true
  WHERE r.ts >= p_from
    AND r.ts <  p_to
  GROUP BY r.sensor_id, r.building_id, bucket_start, lower(coalesce(resolved_unit.aggregation_method, 'mean'))
)
INSERT INTO public.sensor_data (sensor_id, building_id, ts, value, value_text, value_bool)
SELECT sensor_id, building_id, bucket_start, agg_value, agg_value_text, agg_value_bool
FROM bucketed
ON CONFLICT (sensor_id, ts)
DO UPDATE SET
  value      = EXCLUDED.value,
  value_text = EXCLUDED.value_text,
  value_bool = EXCLUDED.value_bool;
$$;

CREATE OR REPLACE FUNCTION public.run_aggregate_sensor_data_5m()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM public.aggregate_sensor_data_5m(now() - interval '15 minutes', now());
  DELETE FROM public.sensor_data_raw WHERE ts < now() - interval '3 days';
END;
$$;

-- Dashboard time grid function: 5h past + 3h future, 5-min intervals
CREATE OR REPLACE FUNCTION public.dashboard_time_grid(
    in_building_id INTEGER,
    in_ref_now TIMESTAMPTZ DEFAULT now(),
    in_past_range INTERVAL DEFAULT public.default_dashboard_past_range(),
    in_future_range INTERVAL DEFAULT public.default_dashboard_future_range()
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
WITH bucket_step_cte AS (
    SELECT public.five_minute_interval() AS step
),
params AS (
    SELECT
        in_building_id AS building_id,
        date_bin((SELECT step FROM bucket_step_cte), in_ref_now, public.unix_epoch_utc()) AS ref_now,
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
    ORDER BY abs(wc.lat - b.lat) + abs(wc.lon - b.lon) ASC
    LIMIT 1
),
grid AS (
    SELECT DISTINCT ts
    FROM (
        SELECT
            date_bin(
                (SELECT step FROM bucket_step_cte),
                sd.ts,
                public.unix_epoch_utc()
            ) AS ts
        FROM public.sensor_data sd
        JOIN public.sensors s ON s.id = sd.sensor_id
        JOIN params p ON s.building_id = p.building_id
        WHERE sd.ts >= p.ref_now - p.past_range
          AND sd.ts <= p.ref_now
        UNION ALL
        SELECT generate_series(
            p.ref_now,
            p.ref_now + p.future_range,
            (SELECT step FROM bucket_step_cte)
        ) AS ts
        FROM params p
    ) timeline
),
sensors AS (
    SELECT
        s.id,
        lower(s.sensor_type) AS type
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
          AND sd.ts <= g.ts
        ORDER BY sd.ts DESC
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
        COALESCE(bool_or(zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off'), false) AS hvac_is_on,
        max(zs.setpoint_c::double precision) FILTER (WHERE zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off') AS hvac_setpoint,
        count(*) FILTER (WHERE zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off') AS active_hvac_intervals
    FROM grid g
    CROSS JOIN params p
    LEFT JOIN public.zone_states zs
      ON zs.ts = g.ts
     AND EXISTS (
         SELECT 1 FROM public.hvac_zones hz
         WHERE hz.id = zs.zone_id AND hz.building_id = p.building_id
     )
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
          AND COALESCE(o.window_start, o.optimization_time) <= g.ts
          AND g.ts < COALESCE(o.window_end, o.optimization_time + interval '1 hour')
        ORDER BY o.optimization_time DESC
        LIMIT 1
    ) o ON true
),
sensor_aggregates AS (
    SELECT
        g.ts,
        MAX(CASE WHEN sv.type = public.temperature_sensor_type() THEN sv.value END) AS temperature,
        MAX(CASE WHEN sv.type = public.presence_sensor_type() THEN sv.value END) AS presence,
        MAX(CASE WHEN sv.type = public.energy_sensor_type() THEN sv.value END) AS energy
    FROM grid g
    LEFT JOIN sensor_values sv ON sv.ts = g.ts
    GROUP BY g.ts
),
context_values AS (
    SELECT
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
    FROM grid g
    LEFT JOIN weather_values wv ON wv.ts = g.ts
    LEFT JOIN hvac_values hv ON hv.ts = g.ts
    LEFT JOIN energy_values ev ON ev.ts = g.ts
)
SELECT
    g.ts,
    sa.temperature,
    sa.presence,
    sa.energy,
    cv.outdoor_temperature,
    cv.outdoor_humidity,
    cv.outdoor_pressure,
    cv.wind_speed,
    cv.wind_direction,
    cv.precipitation,
    cv.weather_description,
    cv.weather_source_timestamp,
    cv.hvac_is_on,
    cv.hvac_setpoint,
    cv.active_hvac_intervals,
    cv.optimization_time,
    cv.input_hash,
    cv.output_hash,
    cv.energy_saving_kwh,
    cv.baseline_consumption_kwh,
    cv.optimized_consumption_kwh,
    cv.environmental_points,
    cv.notes,
    cv.is_optimized
FROM grid g
LEFT JOIN sensor_aggregates sa ON sa.ts = g.ts
LEFT JOIN context_values cv ON cv.ts = g.ts
ORDER BY g.ts ASC;
$$ LANGUAGE sql;


-- Efficiency tool function: measured history + forecast future, both on 5-minute buckets.
CREATE OR REPLACE FUNCTION public.efficiency_tool_timeseries(
    in_building_id  INTEGER,
    in_ref_now      TIMESTAMPTZ DEFAULT now(),
    in_past_range   INTERVAL    DEFAULT public.default_dashboard_past_range(),
    in_future_range INTERVAL    DEFAULT public.default_dashboard_future_range(),
    in_hvac_unit_id INTEGER     DEFAULT NULL
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
WITH bucket_step_cte AS (
    SELECT public.five_minute_interval() AS step
),
params AS (
    SELECT
        in_building_id AS building_id,
        date_bin((SELECT step FROM bucket_step_cte), in_ref_now, public.unix_epoch_utc()) AS ref_now,
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
    ORDER BY abs(wc.lat - b.lat) + abs(wc.lon - b.lon) ASC
    LIMIT 1
),
-- When a specific HVAC unit is requested, resolve its primary zone once
-- so both history and forecast can filter zone_states consistently.
active_zone AS (
    SELECT hz.id AS zone_id
    FROM public.hvac_zones hz
    JOIN public.zone_hvac_units zhu ON zhu.zone_id = hz.id
    WHERE hz.building_id = in_building_id
      AND (in_hvac_unit_id IS NULL OR zhu.hvac_unit_id = in_hvac_unit_id)
    ORDER BY hz.id ASC
    LIMIT 1
),
history_rows AS (
    SELECT
        gsw.sensor_timestamp::timestamptz AS ts,
        'history'::text AS data_kind,
        MAX(CASE WHEN lower(gsw.sensor_type) = public.temperature_sensor_type() THEN gsw.sensor_value END) AS temperature,
        MAX(CASE WHEN lower(gsw.sensor_type) = public.presence_sensor_type() THEN gsw.sensor_value END) AS presence,
        MAX(CASE WHEN lower(gsw.sensor_type) = public.energy_sensor_type() THEN gsw.sensor_value END) AS energy,
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
        p.ref_now::timestamp,
        in_hvac_unit_id
    ) gsw
    GROUP BY gsw.sensor_timestamp
),
forecast_grid AS (
    SELECT generate_series(
        p.ref_now + (SELECT step FROM bucket_step_cte),
        p.ref_now + p.future_range,
        (SELECT step FROM bucket_step_cte)
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
        COALESCE(bool_or(zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off'), false) AS hvac_is_on,
        max(zs.setpoint_c::double precision) FILTER (WHERE zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off') AS hvac_setpoint,
        count(*) FILTER (WHERE zs.hvac_status IS NOT NULL AND zs.hvac_status <> 'off') AS active_hvac_intervals,
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
    LEFT JOIN public.zone_states zs
      ON zs.ts = fw.ts
     AND EXISTS (
         SELECT 1 FROM public.hvac_zones hz
         WHERE hz.id = zs.zone_id
           AND hz.building_id = p.building_id
           AND (in_hvac_unit_id IS NULL OR hz.id = (SELECT zone_id FROM active_zone))
     )
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
          AND COALESCE(o.window_start, o.optimization_time) <= fw.ts
          AND fw.ts < COALESCE(o.window_end, o.optimization_time + interval '1 hour')
          AND (
              in_hvac_unit_id IS NULL
              OR o.hvac_unit_id = in_hvac_unit_id
              OR o.hvac_unit_id IS NULL
          )
        ORDER BY
            CASE WHEN o.hvac_unit_id IS NOT DISTINCT FROM in_hvac_unit_id THEN 0 ELSE 1 END,
            o.optimization_time DESC
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
      AND COALESCE(o.window_start, o.optimization_time) <= h.ts
      AND h.ts < COALESCE(o.window_end, o.optimization_time + interval '1 hour')
      AND (
          in_hvac_unit_id IS NULL
          OR o.hvac_unit_id = in_hvac_unit_id
          OR o.hvac_unit_id IS NULL
      )
    ORDER BY
        CASE WHEN o.hvac_unit_id IS NOT DISTINCT FROM in_hvac_unit_id THEN 0 ELSE 1 END,
        o.optimization_time DESC
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
ORDER BY ts ASC;
$$;

SELECT cron.schedule(
  'aggregate-sensor-data-5m',
  '* * * * *',
  $$SELECT public.run_aggregate_sensor_data_5m();$$
)
WHERE NOT EXISTS (
  SELECT 1
  FROM cron.job
  WHERE jobname = 'aggregate-sensor-data-5m'
);

