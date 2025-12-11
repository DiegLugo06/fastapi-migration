"""
Unit tests for client endpoints with execution time measurement
"""
import time
import statistics
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock

from app.apps.client.models import Cliente


class TestCreateClientePerformance:
    """Performance tests for POST /api/client/cliente endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_cliente_execution_time(
        self,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Test create_cliente endpoint execution time"""
        # Note: Functions like is_valid_identification, _send_client_notification, 
        # and sync_client_with_crm are not yet implemented in FastAPI router
        
        # Test data
        test_data = {
            "name": "Juan",
            "first_last_name": "Pérez",
            "phone": "+521234567890",
            "email": "juan.perez.test@example.com",
            "user_id": mock_user.id,
            "flow_process": "normal",
            "curp": "PEPJ800101HDFRXN01",
            "birth_date": "1980-01-01",
            "street_address": "Calle Principal 123",
            "zip_code": "01000",
            "ciudad": "Ciudad de México",
            "estado": "CDMX"
        }
        
        # Measure execution time
        start_time = time.perf_counter()
        
        response = authenticated_client.post(
            "/api/client/cliente",
            json=test_data
        )
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data.get('success') is True
        assert 'cliente_id' in response_data or 'cliente' in response_data
        
        # Performance assertion - should complete in reasonable time (< 2 seconds)
        assert execution_time < 2.0, f"Endpoint took {execution_time:.4f}s, expected < 2.0s"
        
        print(f"\n✓ Create Cliente - Execution Time: {execution_time:.4f} seconds")
        print(f"  Status: {response.status_code}")
        print(f"  Client ID: {response_data.get('cliente_id')}")
    
    @pytest.mark.asyncio
    async def test_create_cliente_performance_multiple_requests(
        self,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Test performance with multiple sequential requests"""
        
        execution_times = []
        num_requests = 10
        
        for i in range(num_requests):
            test_data = {
                "name": f"Test{i}",
                "first_last_name": "User",
                "phone": f"+5212345678{i:02d}",
                "email": f"test{i}@example.com",
                "user_id": mock_user.id,
                "flow_process": "normal"
            }
            
            start_time = time.perf_counter()
            
            response = authenticated_client.post(
                "/api/client/cliente",
                json=test_data
            )
            
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
            
            # Verify each request succeeded
            assert response.status_code == status.HTTP_201_CREATED
        
        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        print(f"\n📊 Performance Test Results ({num_requests} requests):")
        print(f"  Average: {avg_time:.4f} seconds")
        print(f"  Median:  {median_time:.4f} seconds")
        print(f"  Min:     {min_time:.4f} seconds")
        print(f"  Max:     {max_time:.4f} seconds")
        print(f"  Std Dev: {std_dev:.4f} seconds")
        print(f"  Total:   {sum(execution_times):.4f} seconds")
        
        # Performance assertions
        assert avg_time < 1.0, f"Average time {avg_time:.4f}s exceeds 1.0s threshold"
        assert max_time < 2.0, f"Max time {max_time:.4f}s exceeds 2.0s threshold"
    
    @pytest.mark.asyncio
    async def test_create_cliente_validation_error_time(
        self,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Test execution time for validation error case"""
        # FastAPI will validate the request schema, so invalid data will return 422
        
        test_data = {
            "name": "Invalid",
            "phone": "+521234567890",
            "email": "invalid@example.com",
            "user_id": mock_user.id
        }
        
        start_time = time.perf_counter()
        
        response = authenticated_client.post(
            "/api/client/cliente",
            json=test_data
        )
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # FastAPI returns 422 for validation errors (Pydantic validation)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Validation errors should be fast (< 0.5s)
        assert execution_time < 0.5, f"Validation error took {execution_time:.4f}s, expected < 0.5s"
        
        print(f"\n✓ Validation Error - Execution Time: {execution_time:.4f} seconds")
    
    @pytest.mark.asyncio
    async def test_create_cliente_missing_user_id_time(
        self,
        authenticated_client,
        test_session
    ):
        """Test execution time for missing user_id error"""
        test_data = {
            "name": "Test",
            "phone": "+521234567890",
            "email": "test@example.com",
            # Missing user_id
        }
        
        start_time = time.perf_counter()
        
        response = authenticated_client.post(
            "/api/client/cliente",
            json=test_data
        )
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # FastAPI returns 422 for missing required fields (Pydantic validation)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Early validation should be very fast
        assert execution_time < 0.1, f"Missing user_id check took {execution_time:.4f}s, expected < 0.1s"
        
        print(f"\n✓ Missing user_id - Execution Time: {execution_time:.4f} seconds")
    
    @pytest.mark.asyncio
    async def test_create_cliente_finva_web_flow_time(
        self,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Test execution time for finva web process flow"""
        
        # Create mock finva agent
        finva_agent = MagicMock()
        finva_agent.id = 888
        finva_agent.name = "Finva"
        finva_agent.first_last_name = "Agent"
        finva_agent.email = "finva.agent@example.com"
        finva_agent.uuid = "223e4567-e89b-12d3-a456-426614174000"
        finva_agent.role_id = 9
        finva_agent.is_active = True
        
        test_data = {
            "name": "Finva",
            "first_last_name": "Client",
            "phone": "+521234567895",
            "email": "finva.client@example.com",
            "user_id": mock_user.id,
            "flow_process": "onCreditWeb",  # Finva web process
            "finva_user_id": 888
        }
        
        start_time = time.perf_counter()
        
        response = authenticated_client.post(
            "/api/client/cliente",
            json=test_data
        )
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        assert response.status_code == status.HTTP_201_CREATED
        
        print(f"\n✓ Finva Web Flow - Execution Time: {execution_time:.4f} seconds")


class TestCreateClienteBenchmark:
    """Benchmark tests for create_cliente endpoint"""
    
    @pytest.mark.asyncio
    async def test_benchmark_100_requests(
        self,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Benchmark: 100 sequential requests"""
        
        execution_times = []
        num_requests = 100
        
        overall_start = time.perf_counter()
        
        for i in range(num_requests):
            test_data = {
                "name": f"Bench{i}",
                "first_last_name": "Test",
                "phone": f"+5212345678{i:03d}",
                "email": f"bench{i}@example.com",
                "user_id": mock_user.id,
                "flow_process": "normal"
            }
            
            start_time = time.perf_counter()
            
            response = authenticated_client.post(
                "/api/client/cliente",
                json=test_data
            )
            
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        
        overall_end = time.perf_counter()
        total_time = overall_end - overall_start
        
        # Statistics
        avg_time = statistics.mean(execution_times)
        p95_time = statistics.quantiles(execution_times, n=20)[18] if len(execution_times) > 1 else avg_time
        p99_time = statistics.quantiles(execution_times, n=100)[98] if len(execution_times) > 1 else avg_time
        
        print(f"\n🏆 Benchmark Results ({num_requests} requests):")
        print(f"  Total Time:     {total_time:.4f} seconds")
        print(f"  Average:        {avg_time:.4f} seconds")
        print(f"  95th Percentile: {p95_time:.4f} seconds")
        print(f"  99th Percentile: {p99_time:.4f} seconds")
        print(f"  Requests/sec:   {num_requests / total_time:.2f}")
        
        # Performance thresholds
        assert avg_time < 0.5, f"Average time {avg_time:.4f}s exceeds 0.5s"
        assert p95_time < 1.0, f"95th percentile {p95_time:.4f}s exceeds 1.0s"

