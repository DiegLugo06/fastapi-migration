# Performance Testing Guide

## Viewing Performance Metrics

The performance tests print detailed statistics including:
- **Average** execution time
- **Median** execution time  
- **Min/Max** execution times
- **Standard Deviation** (where applicable)
- **Total** time for multiple requests
- **Percentiles** (P95, P99 for benchmark tests)

## Running Performance Tests

### View All Performance Metrics

Use the `-s` flag to see print statements:

```bash
# Run all performance tests
pytest -k "Performance" -v -s

# Run specific performance test
pytest tests/test_product.py::TestGetMotorcycleModelsPerformance -v -s

# Run all tests with performance output
pytest tests/ -v -s
```

### Quick Commands

```bash
# Product endpoint performance
pytest tests/test_product.py::TestGetMotorcycleModelsPerformance -v -s

# Quote endpoint performance  
pytest tests/test_quote.py::TestGenerateBankQuotesPerformance -v -s

# Client endpoint performance
pytest tests/test_client.py::TestCreateClientePerformance -v -s

# All performance tests
pytest -k "Performance" -v -s
```

## Example Output

```
[PERFORMANCE] Get Motorcycle Models Endpoint:
  Average: 0.1069s
  Median: 0.0727s
  Min: 0.0598s
  Max: 0.4096s
  Iterations: 10

📊 Performance Test Results (10 requests):
  Average: 0.0481 seconds
  Median:  0.0463 seconds
  Min:     0.0335 seconds
  Max:     0.0897 seconds
  Std Dev: 0.0156 seconds
  Total:   0.4809 seconds
```

## Performance Thresholds

- **Product Endpoint**: Average < 1.0s
- **Quote Endpoint**: Average < 5.0s
- **Client Endpoint**: Average < 1.0s, Max < 2.0s

## Tips

- Use `-s` flag to see all print statements
- Use `-v` for verbose output showing which tests are running
- Use `--tb=short` for shorter tracebacks
- Performance metrics are printed during test execution

