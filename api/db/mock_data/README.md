# Mock Data Directory

This directory contains SQL files for initializing the database with sample data for development and testing purposes.

## Files Structure

- `services_data.sql` - Initial services data with 10 predefined services
- `knowledge_data.sql` - Knowledge base assets for various domains
- `predictor_data.sql` - Machine learning predictor models with performance scores

## How It Works

The mock data is automatically loaded when the FastAPI application starts via:

1. `main.py` calls `insert_mock_data()`
2. `utils/mock_data.py` executes the SQL files in this directory
3. Database tables are populated with initial data

## Adding New Mock Data

To add new mock data:

1. Create a new SQL file in this directory (e.g., `new_table_data.sql`)
2. Add the corresponding function in `utils/mock_data.py`
3. Call the function from `insert_mock_data()`

## SQL File Format

Each SQL file should:
- Include descriptive comments
- Use IF NOT EXISTS for indexes
- Include verification queries (commented out)
- Follow the naming convention: `{table_name}_data.sql`

## Usage

The mock data is inserted only if the respective tables are empty, preventing duplicate data on application restarts.
