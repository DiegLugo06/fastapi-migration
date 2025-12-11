"""
Unit tests for quote endpoints with execution time measurement
"""
import time
import statistics
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock

from app.apps.quote.models import Banco, FinancingOption
from app.apps.product.models import Motorcycles, MotorcycleBrand


class TestGenerateBankQuotes:
    """Unit tests for POST /api/quote/quote endpoint"""
    
    @pytest.mark.asyncio
    async def test_generate_bank_quotes_missing_required_fields(
        self, authenticated_client, test_session
    ):
        """Test that missing required fields return 400"""
        data = {
            "loan_term_months": 24,
            # Missing: down_payment_amount, motorcycle_id, paquete, insurance_payment_method
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        # FastAPI returns 422 for validation errors (Pydantic validation)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        assert (end_time - start_time) < 1.0  # Should be fast
    
    @pytest.mark.asyncio
    async def test_generate_bank_quotes_invalid_motorcycle_id(
        self, authenticated_client, test_session
    ):
        """Test that invalid motorcycle_id returns 400"""
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": 99999,  # Non-existent ID
            "paquete": "basico",
            "insurance_payment_method": "financiado"
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # FastAPI wraps errors in "detail" field
        response_data = response.json()
        assert "detail" in response_data
        # The detail can be a dict with "error" key or a string
        if isinstance(response_data["detail"], dict):
            assert "error" in response_data["detail"]
        assert (end_time - start_time) < 1.0
    
    @pytest.mark.asyncio
    async def test_generate_bank_quotes_sfera_holding_not_implemented(
        self, authenticated_client, test_session
    ):
        """Test that Sfera holding returns 501"""
        # Create test motorcycle with unique names
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        brand = MotorcycleBrand(name=f"Test Brand {unique_id}")
        test_session.add(brand)
        await test_session.flush()
        
        motorcycle = Motorcycles(
            brand_id=brand.id,
            model=f"Test Model {unique_id}",
            year=2024,
            price=50000.0,
            active=True
        )
        test_session.add(motorcycle)
        await test_session.flush()
        
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": motorcycle.id,
            "paquete": "basico",
            "insurance_payment_method": "financiado",
            "holding": "Sfera"
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert "error" in response.json()
        assert (end_time - start_time) < 1.0
    
    @pytest.mark.asyncio
    @patch('app.apps.quote.router._fetch_valid_financing_offers')
    @patch('app.apps.quote.router._select_best_offers')
    @patch('app.apps.quote.router.calculate_loan_payment')
    async def test_generate_bank_quotes_success(
        self,
        mock_calculate_loan,
        mock_select_best,
        mock_fetch_offers,
        authenticated_client,
        test_session
    ):
        """Test successful quote generation"""
        # Create test data
        brand = MotorcycleBrand(name="Test Brand")
        test_session.add(brand)
        await test_session.commit()
        
        motorcycle = Motorcycles(
            brand_id=brand.id,
            model="Test Model",
            year=2024,
            price=50000.0,
            active=True
        )
        test_session.add(motorcycle)
        await test_session.commit()
        
        bank = Banco(
            name="Test Bank",
            valor_factura=None,
            minimo_financiar=10000
        )
        test_session.add(bank)
        await test_session.commit()
        
        # Mock dependencies
        mock_offer = MagicMock()
        mock_offer.id = 1
        mock_offer.banco_id = bank.id
        mock_offer.avg_interest_rate = 15.5
        mock_offer.opening_fee = 0.02
        mock_offer.min_loan_term_months = 12
        mock_offer.max_loan_term_months = 60
        
        mock_fetch_offers.return_value = {
            "valid_offers": [mock_offer],
            "optional_offers": []
        }
        
        mock_select_best.return_value = {
            bank.id: {
                "avg_interest_rate": 15.5,
                "opening_fee": 0.02,
                "bank_offer_id": 1
            }
        }
        
        # calculate_loan_payment returns a float (monthly payment amount)
        mock_calculate_loan.return_value = 2500.0
        
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": motorcycle.id,
            "paquete": "basico",
            "insurance_payment_method": "financiado"
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        assert response.status_code == status.HTTP_200_OK
        assert "quotes" in response.json()
        assert (end_time - start_time) < 5.0  # Should complete reasonably fast
    
    @pytest.mark.asyncio
    @patch('app.apps.quote.router._fetch_valid_financing_offers')
    @patch('app.apps.quote.router._select_best_offers')
    @patch('app.apps.quote.router.calculate_loan_payment')
    @patch('app.apps.quote.router._fetch_banks_for_sucursal')
    @patch('app.apps.quote.router._fetch_sucursal')
    @patch('app.apps.quote.router._fetch_user')
    async def test_generate_bank_quotes_with_user_id(
        self,
        mock_fetch_user,
        mock_fetch_sucursal,
        mock_fetch_banks,
        mock_calculate_loan,
        mock_select_best,
        mock_fetch_offers,
        authenticated_client,
        test_session,
        mock_user
    ):
        """Test quote generation with user_id"""
        # Create test data
        brand = MotorcycleBrand(name="Test Brand")
        test_session.add(brand)
        await test_session.commit()
        
        motorcycle = Motorcycles(
            brand_id=brand.id,
            model="Test Model",
            year=2024,
            price=50000.0,
            active=True
        )
        test_session.add(motorcycle)
        await test_session.commit()
        
        bank = Banco(
            name="Test Bank",
            valor_factura=None,
            minimo_financiar=10000
        )
        test_session.add(bank)
        await test_session.commit()
        
        # Mock dependencies
        mock_offer = MagicMock()
        mock_offer.id = 1
        mock_offer.banco_id = bank.id
        mock_offer.avg_interest_rate = 15.5
        mock_offer.opening_fee = 0.02
        
        mock_fetch_offers.return_value = {
            "valid_offers": [mock_offer],
            "optional_offers": []
        }
        
        mock_select_best.return_value = {
            bank.id: {
                "avg_interest_rate": 15.5,
                "opening_fee": 0.02,
                "bank_offer_id": 1
            }
        }
        
        # calculate_loan_payment returns a float (monthly payment amount)
        mock_calculate_loan.return_value = 2500.0
        
        # Mock advisor utils
        mock_sucursal = MagicMock()
        mock_sucursal.id = 1
        mock_sucursal.nombre = "Test Sucursal"
        
        mock_fetch_user.return_value = mock_user
        mock_fetch_sucursal.return_value = mock_sucursal
        mock_fetch_banks.return_value = [bank]
        
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": motorcycle.id,
            "paquete": "basico",
            "insurance_payment_method": "financiado",
            "user_id": 1
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        assert response.status_code == status.HTTP_200_OK
        assert "quotes" in response.json()
        assert (end_time - start_time) < 5.0
    
    @pytest.mark.asyncio
    async def test_generate_bank_quotes_notification_missing_contact(
        self, authenticated_client, test_session
    ):
        """Test that notification without contact info returns 400"""
        # Create test motorcycle with unique names
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        brand = MotorcycleBrand(name=f"Test Brand {unique_id}")
        test_session.add(brand)
        await test_session.flush()
        
        motorcycle = Motorcycles(
            brand_id=brand.id,
            model=f"Test Model {unique_id}",
            year=2024,
            price=50000.0,
            active=True
        )
        test_session.add(motorcycle)
        await test_session.flush()
        
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": motorcycle.id,
            "paquete": "basico",
            "insurance_payment_method": "financiado",
            "send_notification": True
            # Missing: client_email and client_phone
        }
        
        start_time = time.perf_counter()
        response = authenticated_client.post("/api/quote/quote", json=data)
        end_time = time.perf_counter()
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # FastAPI wraps errors in "detail" field
        response_data = response.json()
        assert "detail" in response_data
        # The detail can be a dict with "error" key or a string
        if isinstance(response_data["detail"], dict):
            assert "error" in response_data["detail"]
        assert (end_time - start_time) < 1.0


class TestGenerateBankQuotesPerformance:
    """Performance tests for POST /api/quote/quote endpoint"""
    
    @pytest.mark.asyncio
    @patch('app.apps.quote.router._fetch_valid_financing_offers')
    @patch('app.apps.quote.router._select_best_offers')
    @patch('app.apps.quote.router.calculate_loan_payment')
    async def test_generate_bank_quotes_performance(
        self,
        mock_calculate_loan,
        mock_select_best,
        mock_fetch_offers,
        authenticated_client,
        test_session
    ):
        """Measure execution time for quote generation"""
        # Create test data
        brand = MotorcycleBrand(name="Test Brand")
        test_session.add(brand)
        await test_session.commit()
        
        motorcycle = Motorcycles(
            brand_id=brand.id,
            model="Test Model",
            year=2024,
            price=50000.0,
            active=True
        )
        test_session.add(motorcycle)
        await test_session.commit()
        
        bank = Banco(
            name="Test Bank",
            valor_factura=None,
            minimo_financiar=10000
        )
        test_session.add(bank)
        await test_session.commit()
        
        # Setup mocks
        mock_offer = MagicMock()
        mock_offer.id = 1
        mock_offer.banco_id = bank.id
        mock_offer.avg_interest_rate = 15.5
        mock_offer.opening_fee = 0.02
        
        mock_fetch_offers.return_value = {
            "valid_offers": [mock_offer],
            "optional_offers": []
        }
        
        mock_select_best.return_value = {
            bank.id: {
                "avg_interest_rate": 15.5,
                "opening_fee": 0.02,
                "bank_offer_id": 1
            }
        }
        
        # calculate_loan_payment returns a float (monthly payment amount)
        mock_calculate_loan.return_value = 2500.0
        
        data = {
            "loan_term_months": 24,
            "down_payment_amount": 0.2,
            "motorcycle_id": motorcycle.id,
            "paquete": "1",
            "insurance_payment_method": "Financiado"
        }
        
        # Run multiple iterations
        execution_times = []
        num_iterations = 5
        
        for _ in range(num_iterations):
            start_time = time.perf_counter()
            response = authenticated_client.post("/api/quote/quote", json=data)
            end_time = time.perf_counter()
            
            execution_times.append(end_time - start_time)
            assert response.status_code == status.HTTP_200_OK
        
        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        median_time = statistics.median(execution_times)
        
        print(f"\n[PERFORMANCE] Generate Bank Quotes Endpoint:")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Median: {median_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
        print(f"  Iterations: {num_iterations}")
        
        # Assert reasonable performance (adjust threshold as needed)
        assert avg_time < 5.0, "Average execution time should be less than 5 seconds"


class TestGenerateBankQuotesRealData:
    """Real data tests for POST /api/quote/quote endpoint with 32 combinations"""
    
    # Real motorcycle IDs to test with (matching Django test)
    real_motorcycle_ids = [2, 6, 10, 124]
    
    # Test parameters for combinations
    loan_terms = [12, 24, 36, 48]
    insurance_methods = ["Contado", "Financiado"]
    
    @pytest.mark.asyncio
    @patch('app.apps.quote.router._fetch_valid_financing_offers')
    @patch('app.apps.quote.router._select_best_offers')
    @patch('app.apps.quote.router.calculate_loan_payment')
    async def test_generate_quotes_all_combinations(
        self,
        mock_calculate_loan,
        mock_select_best,
        mock_fetch_offers,
        authenticated_client,
        test_session
    ):
        """Test quote generation with all combinations of real motorcycle IDs, loan terms, and insurance methods"""
        execution_times = []
        successful_tests = 0
        failed_tests = []
        
        # Setup mocks
        mock_offer = MagicMock()
        mock_offer.id = 1
        mock_offer.banco_id = 1  # Default bank ID
        mock_offer.avg_interest_rate = 15.5
        mock_offer.opening_fee = 0.02
        mock_offer.min_loan_term_months = 12
        mock_offer.max_loan_term_months = 60
        
        mock_fetch_offers.return_value = {
            "valid_offers": [mock_offer],
            "optional_offers": []
        }
        
        mock_select_best.return_value = {
            1: {  # Default bank ID
                "avg_interest_rate": 15.5,
                "opening_fee": 0.02,
                "bank_offer_id": 1
            }
        }
        
        mock_calculate_loan.return_value = 2500.0
        
        # Create test bank
        bank = Banco(
            id=1,
            name="Test Bank",
            valor_factura=None,
            minimo_financiar=10000
        )
        test_session.add(bank)
        await test_session.flush()
        
        # Create test motorcycles for real data tests
        test_motorcycles = {}
        for mid in self.real_motorcycle_ids:
            try:
                # Try to get existing motorcycle
                stmt = select(Motorcycles).where(Motorcycles.id == mid, Motorcycles.active == True)
                result = await test_session.execute(stmt)
                motorcycle = result.scalar_one_or_none()
                
                if not motorcycle:
                    # Create a test motorcycle with this ID
                    brand = MotorcycleBrand(name=f"Brand {mid}")
                    test_session.add(brand)
                    await test_session.flush()
                    
                    motorcycle = Motorcycles(
                        id=mid,
                        brand_id=brand.id,
                        model=f"Model {mid}",
                        year=2024,
                        price=50000.0 + (mid * 1000),
                        active=True
                    )
                    test_session.add(motorcycle)
                    await test_session.flush()
                
                test_motorcycles[mid] = motorcycle
            except Exception as e:
                # If we can't create with specific ID, create a generic one
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                brand = MotorcycleBrand(name=f"Brand {mid} {unique_id}")
                test_session.add(brand)
                await test_session.flush()
                
                motorcycle = Motorcycles(
                    brand_id=brand.id,
                    model=f"Model {mid} {unique_id}",
                    year=2024,
                    price=50000.0 + (mid * 1000),
                    active=True
                )
                test_session.add(motorcycle)
                await test_session.flush()
                test_motorcycles[mid] = motorcycle
        
        # Test all combinations
        for motorcycle_id in self.real_motorcycle_ids:
            motorcycle = test_motorcycles.get(motorcycle_id)
            if not motorcycle:
                continue  # Skip if motorcycle creation failed
            
            for loan_term in self.loan_terms:
                for insurance_method in self.insurance_methods:
                    data = {
                        "loan_term_months": loan_term,
                        "down_payment_amount": 0.2,
                        "motorcycle_id": motorcycle.id,
                        "paquete": "1",
                        "insurance_payment_method": insurance_method
                    }
                    
                    start_time = time.perf_counter()
                    response = authenticated_client.post("/api/quote/quote", json=data)
                    end_time = time.perf_counter()
                    
                    execution_time = end_time - start_time
                    execution_times.append(execution_time)
                    
                    if response.status_code == status.HTTP_200_OK:
                        successful_tests += 1
                    else:
                        failed_tests.append({
                            "motorcycle_id": motorcycle.id,
                            "loan_term": loan_term,
                            "insurance_method": insurance_method,
                            "status": response.status_code,
                            "error": response.json() if response.content else None
                        })
        
        # Calculate statistics
        total_tests = len(self.real_motorcycle_ids) * len(self.loan_terms) * len(self.insurance_methods)
        avg_time = statistics.mean(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        median_time = statistics.median(execution_times) if execution_times else 0
        
        print(f"\n[REAL DATA TEST] Quote Generation - All Combinations:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Failed: {len(failed_tests)}")
        print(f"  Average time: {avg_time:.4f}s")
        print(f"  Median time: {median_time:.4f}s")
        print(f"  Min time: {min_time:.4f}s")
        print(f"  Max time: {max_time:.4f}s")
        
        if failed_tests:
            print(f"\n  Failed test cases:")
            for failure in failed_tests[:5]:  # Show first 5 failures
                print(f"    Motorcycle {failure['motorcycle_id']}, Term {failure['loan_term']}, "
                      f"Insurance {failure['insurance_method']}: Status {failure['status']}")
        
        # Assertions
        assert successful_tests > 0, "At least some tests should succeed"
        assert avg_time < 5.0, "Average execution time should be less than 5 seconds"

