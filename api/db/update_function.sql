-- Update encrypt_wallet function to be deterministic using HMAC
CREATE OR REPLACE FUNCTION encrypt_wallet(wallet_address TEXT, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Use HMAC for deterministic encryption (same input always produces same output)
    -- This allows upsert functionality while still providing security
    RETURN encode(hmac(wallet_address, encryption_key, 'sha256'), 'base64');
END;
$$ LANGUAGE plpgsql;

-- Test the function
SELECT encrypt_wallet('test_wallet', 'test_key') as test1;
SELECT encrypt_wallet('test_wallet', 'test_key') as test2;
SELECT encrypt_wallet('test_wallet', 'test_key') as test3;
