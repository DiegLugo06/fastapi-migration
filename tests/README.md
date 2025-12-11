# FastAPI Migration - Unit Tests

This directory contains unit tests for the FastAPI migration project, adapted from the Django project tests.

## Test Structure

- `conftest.py`: Shared pytest fixtures and configuration
- `test_product.py`: Tests for product endpoints (motorcycle_models)
- `test_quote.py`: Tests for quote endpoints (generate_bank_quotes)
- `test_client.py`: Tests for client endpoints (create_cliente)

## Running Tests

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_product.py
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run performance tests only
```bash
pytest -k "Performance" -v
```

## Test Features

- **Performance Measurement**: All tests measure execution time similar to Django tests
- **Async Support**: Uses pytest-asyncio for async endpoint testing
- **Mocking**: Uses unittest.mock for authentication and external dependencies
- **In-Memory Database**: Uses SQLite in-memory database for fast test execution
- **Fixtures**: Reusable fixtures for test client, database session, and authentication

## Performance Comparison

The tests are designed to match the Django test structure to enable performance comparison:

- Execution time measurement using `time.perf_counter()`
- Statistics calculation (mean, median, min, max)
- Multiple iterations for performance tests
- Benchmark tests for high-volume scenarios

## Notes

- Tests use an in-memory SQLite database for speed
- Authentication is mocked to avoid requiring real Supabase credentials
- External services (email, CRM) are mocked
- Some tests may need adjustment based on actual endpoint implementations

