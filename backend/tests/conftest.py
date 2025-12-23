"""
Pytest configuration and fixtures for backend tests.
"""
import pytest
import os
import sys
import warnings
import traceback
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env in project root (2 levels up from tests/)
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment variables from {env_path}")
    else:
        # Also check in backend directory
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✓ Loaded environment variables from {env_path}")
        else:
            print("⚠ No .env file found, using environment variables and defaults")
except ImportError:
    print("⚠ python-dotenv not installed, skipping .env file loading")
    print("  Install with: pip install python-dotenv")

# Auto-detect if running outside Docker and adjust POSTGRES_HOST
if not os.getenv('POSTGRES_HOST') or os.getenv('POSTGRES_HOST') == 'db':
    # Check if we're in a Docker container
    in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') is not None
    if not in_docker:
        # Running outside Docker, use localhost
        os.environ['POSTGRES_HOST'] = 'localhost'
        print("⚠ Running outside Docker, setting POSTGRES_HOST=localhost")


@pytest.fixture(scope="session")
def db_connection():
    """Create a shared database connection for all tests."""
    conn = None
    try:
        from app.db import get_conn
        conn = get_conn()
        # Test a simple query to ensure DB is working
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        print("\n✓ Database connection successful")
        yield conn
        if conn:
            conn.close()
            print("✓ Database connection closed")
    except ImportError as e:
        print(f"\n❌ Missing dependency:")
        print(f"   Error: {e}")
        print(f"   Install dependencies with: pip install -r requirements.txt")
        print(f"   Or: pip install psycopg2-binary")
        # Don't skip - let tests fail with proper error
        yield None
    except Exception as e:
        print(f"\n❌ Database connection failed:")
        print(f"   Error: {e}")
        print(f"   Traceback:")
        traceback.print_exc()
        print(f"\n   Make sure:")
        print(f"   - Database is running")
        print(f"   - Conda environment 'wonderful' is activated")
        print(f"   - Environment variables are set correctly (from .env or environment):")
        print(f"     POSTGRES_HOST={os.getenv('POSTGRES_HOST', 'db')}")
        print(f"     POSTGRES_PORT={os.getenv('POSTGRES_PORT', '5432')}")
        print(f"     POSTGRES_DB={os.getenv('POSTGRES_DB', 'pharmacy')}")
        print(f"     POSTGRES_USER={os.getenv('POSTGRES_USER', 'pharmacy_user')}")
        pwd = os.getenv('POSTGRES_PASSWORD', 'pharmacy_pass')
        print(f"     POSTGRES_PASSWORD={'*' * len(pwd) if pwd else '(not set)'}")
        print(f"   - If using Docker, POSTGRES_HOST should be 'localhost' or '127.0.0.1'")
        print(f"   - If using Docker Compose, check DB_PORT environment variable")
        # Don't skip - let tests fail with proper error messages
        yield None


@pytest.fixture(scope="session")
def db_available(db_connection):
    """Check if database is available."""
    return db_connection is not None


@pytest.fixture(autouse=True)
def check_db_before_test(db_connection):
    """Check database availability before each test."""
    # Connection is already established in db_connection fixture
    # If connection is None, tests will fail with proper error messages
    if db_connection is None:
        print("\n⚠ Warning: Database connection not available. Tests may fail.")
    pass


@pytest.fixture
def sample_medication_data():
    """Sample medication data for testing."""
    return {
        "med_id": "MED001",
        "brand_name": "Nurofen",
        "generic_name": "Ibuprofen",
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "1001",
        "email": "user1001@example.com",
    }
