# Database Directory

This directory contains all database-related files for the QoE Application.

## Structure

```
db/
├── __init__.py                 # Package initialization with functions
├── connection.py              # Database connection configuration
├── docker-compose.yml         # PostgreSQL Docker setup
├── init.sql                   # Database initialization script with encryption
├── mock_data.py              # PostgreSQL-compatible mock data loader
├── README.md                 # This file
├── functions/                # Database utility functions
│   ├── __init__.py
│   └── rating_functions.py   # Rating-related functions with encryption
└── mock_data/                # Mock data SQL files
    ├── services_data.sql     # Sample services (PostgreSQL compatible)
    ├── knowledge_data.sql    # Sample knowledge data
    └── predictor_data.sql    # Sample predictor data
```

## Quick Start

### 1. Start PostgreSQL Database

```bash
cd api/db
docker-compose up -d
```

### 2. Install Dependencies

```bash
conda install psycopg2
# or
pip install psycopg2-binary
```

### 3. Environment Variables

Your `.env` file should contain:

```bash
DATABASE_URL=postgresql://qoe_user:qoe_password@localhost:5432/qoe_database
RATING_ENCRYPTION_KEY=qoe-super-secret-encryption-key-2024-v1
SESSION_SECRET_KEY=your-session-secret-key
AUTH_TYPE=cookie
```

### 4. Run Your Application

```bash
cd api
python main.py
# or
uvicorn main:app --reload
```

The database will automatically:
- Create all tables
- Run encryption setup from `init.sql`
- Load mock data from `mock_data.py`

## Database Features

### 🔒 Encryption
- Wallet addresses encrypted using AES with `pgcrypto`
- Custom encryption keys from environment variables
- Privacy-preserving rating system

### 📊 Rating System
- One rating per wallet per service (upsert mechanism)
- Encrypted wallet storage
- Aggregated scoring without exposing individual wallets
- Rating distribution analytics

### 🔧 Available Functions
- `upsert_rating()` - Submit/update ratings securely
- `calculate_service_score()` - Get service statistics
- `get_top_rated_services()` - Get highest rated services
- `encrypt_wallet()` / `decrypt_wallet()` - Wallet encryption utilities

## API Endpoints

### Rating Endpoints
- **POST** `/rates/submit` - Submit encrypted rating
- **GET** `/rates/service/{id}/score` - Get service score
- **GET** `/rates/my-ratings` - Get user's ratings
- **GET** `/rates/service/{id}/ratings` - Get all service ratings (anonymized)

## Usage Examples

### Submit a Rating
```python
# POST /rates/submit
{
  "service_id": 1,
  "rating": 4.5,
  "feedback": "Great service!"
}
```

### Get Service Score
```python
# GET /rates/service/1/score
{
  "service_id": 1,
  "average_rating": 4.2,
  "total_ratings": 15,
  "rating_distribution": {
    "5_star": 8,
    "4_star": 5,
    "3_star": 2,
    "2_star": 0,
    "1_star": 0
  }
}
```

## Database Management

### Check Database Status
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs postgres
```

### Connect to Database
```bash
docker exec -it qoe-postgres psql -U qoe_user -d qoe_database
```

### Run Mock Data Manually
```bash
cd api
python -c "from db.mock_data import insert_mock_data; insert_mock_data()"
```

### Clear All Data
```bash
python -c "from db.mock_data import clear_all_data; clear_all_data()"
```

### Backup Database
```bash
docker exec qoe-postgres pg_dump -U qoe_user qoe_database > backup.sql
```

### Stop Database
```bash
docker-compose down
```

## Security Notes

- ✅ Wallet addresses encrypted with AES
- ✅ Environment-based key management
- ✅ No plain text wallet storage
- ✅ Privacy-preserving aggregations
- ✅ Secure session management

## Migration from SQLite

The application automatically handles the migration:

1. **Old**: SQLite with plain text wallets
2. **New**: PostgreSQL with encrypted wallets
3. **Backward compatible**: Existing endpoints still work
4. **Enhanced security**: New endpoints use encryption

## Troubleshooting

### Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Import Errors
```bash
# Make sure you're in the right environment
conda activate qoe

# Install missing dependencies
conda install psycopg2
```

### Permission Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d
```
