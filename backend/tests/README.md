# Backend Tests

This directory contains comprehensive tests for the pharmacy backend tools.

## Prerequisites

1. **Activate conda environment:**
   ```bash
   conda activate wonderful
   ```

2. **Install test dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Database must be running and accessible**
   - Database should contain seed data (from `db/init.sql`)
   - Environment variables can be set via:
     - `.env` file in project root or backend directory (automatically loaded)
     - Environment variables
     - Defaults will be used if not set:
       - `POSTGRES_HOST` (default: "db")
       - `POSTGRES_PORT` (default: "5432")
       - `POSTGRES_DB` (default: "pharmacy")
       - `POSTGRES_USER` (default: "pharmacy_user")
       - `POSTGRES_PASSWORD` (default: "pharmacy_pass")
   
   **Note:** If running tests outside Docker, set `POSTGRES_HOST=localhost` or `127.0.0.1`

## Running Tests

### From backend directory (recommended)
```bash
cd backend
pytest tests/test_tools.py -v
```

### From project root
```bash
pytest backend/tests/test_tools.py -v
```

### Run all tests
```bash
cd backend
pytest tests/ -v
```

### Run specific test class
```bash
cd backend
pytest tests/test_tools.py::TestGetMedicationByName -v
```

### Run specific test
```bash
cd backend
pytest tests/test_tools.py::TestGetMedicationByName::test_find_existing_medication_by_brand_name -v
```

### Run with coverage
```bash
cd backend
pytest tests/test_tools.py --cov=app.tools --cov-report=html
```

### Run with database connection check
If tests are being skipped, check database connection:
```bash
cd backend
python3 -c "from app.db import get_conn; conn = get_conn(); print('DB OK'); conn.close()"
```

## Test Structure

- `test_tools.py`: Comprehensive tests for all tool functions
- `conftest.py`: Pytest configuration and fixtures

## Test Coverage

Tests cover:
- ✅ All tool functions
- ✅ Success cases
- ✅ Error cases
- ✅ Edge cases (empty strings, None values, etc.)
- ✅ Parameter validation
- ✅ Database query correctness
- ✅ Return value structure

## Notes

- Tests assume database is running with seed data
- Tests may modify database state (e.g., refill requests)
- Some tests depend on seed data structure - adjust if schema changes

