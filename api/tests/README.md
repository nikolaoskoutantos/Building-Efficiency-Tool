# API Tests

This folder contains test scripts for the QoE Application API, specifically for testing the rating system with encrypted wallet addresses, upsert functionality, and authentication policies.

## Test Files

### 1. `test_upsert.py` *(Basic/No Auth)*
**Purpose**: Tests basic upsert functionality using test endpoints
- Tests that submitting multiple ratings with the same wallet and service updates the existing record
- Verifies that different services create separate records
- Uses `/rates/test-upsert` endpoint (bypasses authentication)
- **Will fail in production** when authentication is enabled

**Usage**:
```bash
cd api/tests
python test_upsert.py
```

### 2. `test_deterministic_encryption.py` *(Basic/No Auth)*
**Purpose**: Tests the deterministic encryption functionality
- Verifies that the same wallet address always produces the same encrypted value
- Tests the complete upsert workflow with deterministic encryption
- **Will fail in production** when authentication is enabled

**Usage**:
```bash
cd api/tests
python test_deterministic_encryption.py
```

### 3. `test_complete_system.py` *(Basic/No Auth)*
**Purpose**: Comprehensive system test covering all functionality
- Tests main endpoint upsert functionality using test endpoints
- **Will fail in production** when authentication is enabled

**Usage**:
```bash
cd api/tests
python test_complete_system.py
```

### 4. `test_authenticated_ratings.py` *(Production-Ready)*
**Purpose**: Tests the rating system with proper authentication and policies
- Tests authenticated rating submissions using `/rates/submit`
- Verifies upsert functionality with real authentication
- Tests policy enforcement (invalid ratings, unauthenticated requests)
- Tests multiple users rating the same service
- **Production-ready** - works with authentication enabled

**Usage**:
```bash
cd api/tests
python test_authenticated_ratings.py
```

### 5. `test_config.py`
**Purpose**: Configuration management for different test environments
- Handles different authentication types (JWT, cookie, mock)
- Supports multiple environments (development, staging, production)
- Manages test vs production endpoints

### 6. `run_tests.py`
**Purpose**: Test runner for basic tests (no authentication)
- Runs the basic test suite that uses test endpoints
- Good for development before adding authentication

## Authentication vs No Authentication

### 🚨 **Important**: Tests will fail differently based on authentication setup:

#### **Before Adding Authentication/Policies:**
- ✅ `test_upsert.py` - Works (uses test endpoints)
- ✅ `test_deterministic_encryption.py` - Works (uses test endpoints) 
- ✅ `test_complete_system.py` - Works (uses test endpoints)
- ❌ `test_authenticated_ratings.py` - May fail (expects auth but none required)

#### **After Adding Authentication/Policies:**
- ❌ `test_upsert.py` - Fails (test endpoints should be removed)
- ❌ `test_deterministic_encryption.py` - Fails (test endpoints should be removed)
- ❌ `test_complete_system.py` - Fails (test endpoints should be removed)
- ✅ `test_authenticated_ratings.py` - Works (designed for production)

## Environment Configuration

Set environment variables to control test behavior:

```bash
# Development without authentication (default)
export TEST_ENV=development_no_auth

# Development with authentication
export TEST_ENV=development_with_auth
export TEST_AUTH_TOKEN=your_jwt_token

# Staging environment
export TEST_ENV=staging
export STAGING_AUTH_TOKEN=your_staging_token

# Production environment (be careful!)
export TEST_ENV=production
export PROD_AUTH_TOKEN=your_production_token
```

## Prerequisites

1. **API Server Running**: Make sure the FastAPI server is running
   ```bash
   cd api
   uvicorn main:app --reload
   ```

2. **Database Running**: Ensure PostgreSQL is running with the correct schema
   ```bash
   cd api/db
   docker-compose up -d
   ```

3. **Python Dependencies**: Install required packages
   ```bash
   pip install requests
   ```

4. **Authentication Setup** (for production tests):
   - Valid JWT tokens for your authentication system
   - Proper environment variables set
   - Authentication middleware configured in FastAPI

## Test Endpoints vs Production Endpoints

### Test Endpoints (Remove in Production):
- `POST /rates/test-upsert` - Bypasses authentication
- `GET /rates/test-view-data` - Bypasses authentication
- Used by basic tests for development

### Production Endpoints:
- `POST /rates/submit` - Requires authentication
- `GET /rates/my-ratings` - Requires authentication
- `GET /rates/service/{id}/score` - May require authentication
- Used by authenticated tests

## Migration Strategy

When adding authentication to your system:

1. **Phase 1**: Run basic tests to ensure core functionality works
   ```bash
   python run_tests.py
   ```

2. **Phase 2**: Add authentication/policies to your API

3. **Phase 3**: Remove test endpoints from production

4. **Phase 4**: Use authenticated tests going forward
   ```bash
   python test_authenticated_ratings.py
   ```

## Expected Results

✅ **Basic tests should pass if:**
- API server running without authentication
- Test endpoints available
- Database connectivity working
- Deterministic encryption implemented

✅ **Authenticated tests should pass if:**
- API server running with authentication
- Valid authentication tokens provided
- Production endpoints working
- Proper policy enforcement

## Security Notes

- Basic tests use hardcoded wallet addresses for testing
- Authenticated tests use mock authentication for development
- Test endpoints should be removed in production
- Never commit real authentication tokens to version control
- Use environment variables for sensitive configuration
