CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.encrypt_wallet(wallet_address TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(hmac(wallet_address, encryption_key, 'sha256'), 'base64');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.decrypt_wallet(encrypted_wallet TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(decode(encrypted_wallet, 'base64'), encryption_key);
EXCEPTION WHEN OTHERS THEN
    RETURN 'HMAC_HASH_NOT_REVERSIBLE';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.upsert_rating(
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
    encrypted_wallet_value := public.encrypt_wallet(p_wallet_address, p_encryption_key);

    SELECT id INTO existing_rate_id
    FROM public.rates
    WHERE rates.service_id = p_service_id
      AND rates.encrypted_wallet = encrypted_wallet_value;

    IF existing_rate_id IS NOT NULL THEN
        UPDATE public.rates
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
            FALSE AS is_new_rating,
            result_record.created_at,
            result_record.updated_at;
    ELSE
        INSERT INTO public.rates (service_id, encrypted_wallet, rating, feedback, created_at, updated_at)
        VALUES (p_service_id, encrypted_wallet_value, p_rating, p_feedback, NOW(), NOW())
        RETURNING rates.id, rates.service_id, rates.rating, rates.feedback, rates.created_at, rates.updated_at
        INTO result_record;

        RETURN QUERY SELECT
            result_record.id,
            result_record.service_id,
            result_record.rating,
            result_record.feedback,
            TRUE AS is_new_rating,
            result_record.created_at,
            result_record.updated_at;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.calculate_service_score(p_service_id INTEGER)
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
        ROUND(AVG(rating)::numeric, 2)::FLOAT AS average_rating,
        COUNT(*)::INTEGER AS total_ratings,
        json_build_object(
            '1_star', COUNT(*) FILTER (WHERE rating >= 1 AND rating < 2),
            '2_star', COUNT(*) FILTER (WHERE rating >= 2 AND rating < 3),
            '3_star', COUNT(*) FILTER (WHERE rating >= 3 AND rating < 4),
            '4_star', COUNT(*) FILTER (WHERE rating >= 4 AND rating < 5),
            '5_star', COUNT(*) FILTER (WHERE rating = 5)
        ) AS rating_distribution
    FROM public.rates
    WHERE rates.service_id = p_service_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_top_rated_services(limit_count INTEGER DEFAULT 10)
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
        ROUND(AVG(r.rating)::numeric, 2)::FLOAT AS avg_rating,
        COUNT(r.id)::INTEGER AS total_count
    FROM public.services s
    INNER JOIN public.rates r ON s.id = r.service_id
    WHERE s.is_active = 1
    GROUP BY s.id, s.name
    HAVING COUNT(r.id) >= 3
    ORDER BY avg_rating DESC, total_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
