CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Update encrypt_wallet function to be deterministic using HMAC
CREATE OR REPLACE FUNCTION encrypt_wallet(wallet_address TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Use HMAC for deterministic encryption (same input always produces same output)
    -- This allows upsert functionality while still providing security
    RETURN encode(hmac(wallet_address::bytea, encryption_key::bytea, 'sha256'), 'base64');
END;
$$ LANGUAGE plpgsql;


-- Test the function with deduplicated literals
WITH test_values AS (
    SELECT 'test_wallet' AS wallet, 'test_key' AS key
)
SELECT encrypt_wallet(wallet, key) as test1 FROM test_values;
SELECT encrypt_wallet(wallet, key) as test2 FROM test_values;
SELECT encrypt_wallet(wallet, key) as test3 FROM test_values;
