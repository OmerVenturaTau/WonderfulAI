"""
Comprehensive tests for pharmacy tools.

These tests assume the database is running and contains seed data.
Run with: pytest backend/tests/test_tools.py -v
Or from backend directory: pytest tests/test_tools.py -v
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools import (
    get_medication_by_name,
    list_medications,
    search_users,
    check_stock_availability,
    list_user_prescriptions,
    query_medications_flexible,
    query_medications_with_stock,
    query_stock_multiple_stores,
    list_stores,
    query_prescriptions_flexible,
    request_prescription_refill,
    run_tool,
)


class TestGetMedicationByName:
    """Tests for get_medication_by_name tool."""
    
    def test_find_existing_medication_by_brand_name(self):
        """Test finding medication by brand name."""
        try:
            result = get_medication_by_name("Nurofen")
            print(f"\nDEBUG: Result for 'Nurofen': {result}")
            
            # Check that we got a result (either found or with candidates)
            assert "found" in result, f"Result missing 'found' key: {result}"
            
            if not result["found"]:
                # If not found, should have candidates or fuzzy matches
                print(f"DEBUG: Medication not found. Result: {result}")
                assert "candidates" in result or "fuzzy" in result, f"Not found but no candidates: {result}"
                pytest.skip("Medication not found - database may not have seed data")
            
            assert result["found"] is True, f"Expected found=True, got {result['found']}"
            assert "med" in result, f"Result missing 'med' key: {result}"
            assert result["med"]["brand_name"] == "Nurofen", f"Expected brand_name='Nurofen', got '{result['med'].get('brand_name')}'"
            assert result["med"]["generic_name"] == "Ibuprofen", f"Expected generic_name='Ibuprofen', got '{result['med'].get('generic_name')}'"
            # active_ingredients is a list, check if Ibuprofen is in the list
            active_ingredients = result["med"]["active_ingredients"]
            assert isinstance(active_ingredients, list), f"active_ingredients should be list, got {type(active_ingredients)}: {active_ingredients}"
            assert any("Ibuprofen" in ing for ing in active_ingredients), f"Ibuprofen not found in {active_ingredients}"
        except Exception as e:
            print(f"\n❌ Test failed with exception:")
            import traceback
            traceback.print_exc()
            raise
    
    def test_find_existing_medication_by_generic_name(self):
        """Test finding medication by generic name."""
        try:
            result = get_medication_by_name("Ibuprofen")
            print(f"\nDEBUG: Result for 'Ibuprofen': {result}")
            assert "found" in result, f"Result missing 'found' key: {result}"
            
            if not result["found"]:
                print(f"DEBUG: Medication not found. Result: {result}")
                assert "candidates" in result or "fuzzy" in result
                pytest.skip("Medication not found - database may not have seed data")
            
            assert result["found"] is True, f"Expected found=True, got {result.get('found')}"
            assert result["med"]["generic_name"] == "Ibuprofen", f"Expected generic_name='Ibuprofen', got '{result['med'].get('generic_name')}'"
        except Exception as e:
            print(f"\n❌ Test failed with exception:")
            import traceback
            traceback.print_exc()
            raise
    
    def test_find_existing_medication_by_active_ingredient(self):
        """Test finding medication by active ingredient."""
        try:
            result = get_medication_by_name("Paracetamol")
            print(f"\nDEBUG: Result for 'Paracetamol': {result}")
            assert "found" in result, f"Result missing 'found' key: {result}"
            
            if not result["found"]:
                print(f"DEBUG: Medication not found. Result: {result}")
                assert "candidates" in result or "fuzzy" in result
                pytest.skip("Medication not found - database may not have seed data")
            
            assert result["found"] is True, f"Expected found=True, got {result.get('found')}"
            # active_ingredients is a list
            active_ingredients = result["med"]["active_ingredients"]
            assert isinstance(active_ingredients, list), f"active_ingredients should be list, got {type(active_ingredients)}: {active_ingredients}"
            assert any("Paracetamol" in ing for ing in active_ingredients), f"Paracetamol not found in {active_ingredients}"
        except Exception as e:
            print(f"\n❌ Test failed with exception:")
            import traceback
            traceback.print_exc()
            raise
    
    def test_medication_not_found(self):
        """Test handling of non-existent medication."""
        result = get_medication_by_name("NonExistentMed123")
        assert result["found"] is False
        assert "candidates" in result or "fuzzy" in result
    
    def test_fuzzy_matching_typo(self):
        """Test fuzzy matching handles typos."""
        result = get_medication_by_name("iburprofen")  # Typo
        # Should either find it or suggest fuzzy matches
        assert "found" in result
        if not result["found"]:
            assert "fuzzy" in result or "candidates" in result
    
    def test_ambiguous_results(self):
        """Test handling of ambiguous medication names."""
        # This depends on your seed data - adjust if needed
        result = get_medication_by_name("Tablet")
        # Should return ambiguous or candidates
        assert "found" in result


class TestListMedications:
    """Tests for list_medications tool."""
    
    def test_list_all_medications(self):
        """Test listing all medications."""
        result = list_medications(limit=100)
        assert "medications" in result
        assert "count" in result
        assert isinstance(result["medications"], list)
        assert result["count"] > 0
    
    def test_search_medications_by_term(self):
        """Test searching medications by search term."""
        result = list_medications(search_term="ibuprofen", limit=10)
        assert "medications" in result
        assert result["count"] > 0
        # All results should contain the search term in some field
        for med in result["medications"]:
            assert (
                "ibuprofen" in med["brand_name"].lower() or
                "ibuprofen" in med["generic_name"].lower() or
                "ibuprofen" in med["active_ingredients"].lower()
            )
    
    def test_limit_parameter(self):
        """Test limit parameter works."""
        result = list_medications(limit=2)
        assert result["count"] <= 2
    
    def test_empty_search_results(self):
        """Test search with term that doesn't match."""
        result = list_medications(search_term="XYZ123NonExistent", limit=10)
        assert "medications" in result
        assert result["count"] == 0


class TestSearchUsers:
    """Tests for search_users tool."""
    
    def test_search_by_user_id(self):
        """Test searching user by ID."""
        result = search_users(user_id="1001")
        assert result["count"] > 0
        assert result["users"][0]["user_id"] == "1001"
    
    def test_search_by_name(self):
        """Test searching user by name."""
        result = search_users(name="User 1001")
        assert result["count"] > 0
        assert "1001" in result["users"][0]["user_id"]
    
    def test_search_by_email(self):
        """Test searching user by email."""
        result = search_users(email="user1001@example.com")
        assert result["count"] > 0
        assert "user1001@example.com" in result["users"][0]["email"]
    
    def test_search_by_phone(self):
        """Test searching user by phone."""
        result = search_users(phone="+972-50-00001001")
        assert result["count"] > 0
    
    def test_no_search_parameters_error(self):
        """Test error when no search parameters provided."""
        result = search_users()
        assert "error" in result
        assert "At least one search parameter" in result["error"]


class TestCheckStockAvailability:
    """Tests for check_stock_availability tool."""
    
    def test_check_stock_existing(self):
        """Test checking stock for existing medication."""
        result = check_stock_availability("MED001", "STORE_TLV_01")
        assert "med_id" in result
        assert "store_id" in result
        assert "quantity" in result
        assert "status" in result
        assert result["status"] in ["in_stock", "out_of_stock"]
    
    def test_check_stock_not_found(self):
        """Test checking stock for non-existent entry."""
        result = check_stock_availability("MED999", "STORE_TLV_01")
        assert "error" in result
        assert result["error"] == "NOT_FOUND"


class TestListUserPrescriptions:
    """Tests for list_user_prescriptions tool."""
    
    def test_list_prescriptions_existing_user(self):
        """Test listing prescriptions for user with prescriptions."""
        result = list_user_prescriptions("1003")
        assert "prescriptions" in result
        assert "user_id" in result
        assert result["user_id"] == "1003"
        assert isinstance(result["prescriptions"], list)
    
    def test_list_prescriptions_user_without_prescriptions(self):
        """Test listing prescriptions for user without prescriptions."""
        result = list_user_prescriptions("1001")
        assert "prescriptions" in result
        assert result["prescriptions"] == []


class TestQueryMedicationsFlexible:
    """Tests for query_medications_flexible tool."""
    
    def test_filter_by_rx_required(self):
        """Test filtering by prescription requirement."""
        result = query_medications_flexible(rx_required=False, limit=10)
        assert "medications" in result
        for med in result["medications"]:
            assert med["rx_required"] is False
    
    def test_filter_by_form(self):
        """Test filtering by form."""
        result = query_medications_flexible(form="Tablet", limit=10)
        assert "medications" in result
        for med in result["medications"]:
            assert "tablet" in med["form"].lower()
    
    def test_filter_by_active_ingredient(self):
        """Test filtering by active ingredient."""
        result = query_medications_flexible(active_ingredient="Ibuprofen", limit=10)
        assert "medications" in result
        for med in result["medications"]:
            assert "ibuprofen" in med["active_ingredients"].lower()
    
    def test_multiple_filters(self):
        """Test combining multiple filters."""
        result = query_medications_flexible(
            form="Tablet",
            rx_required=False,
            limit=10
        )
        assert "medications" in result
        for med in result["medications"]:
            assert "tablet" in med["form"].lower()
            assert med["rx_required"] is False


class TestQueryMedicationsWithStock:
    """Tests for query_medications_with_stock tool."""
    
    def test_query_with_stock_filter(self):
        """Test querying medications with stock filtering."""
        result = query_medications_with_stock(
            search_term="Nurofen",
            store_ids=["STORE_TLV_01"],
            limit=10
        )
        assert "medications" in result
        assert result["count"] > 0
        # Check that stock info is included
        for med in result["medications"]:
            assert "stock" in med
            assert isinstance(med["stock"], list)
    
    def test_query_in_stock_only(self):
        """Test filtering to only in-stock medications."""
        result = query_medications_with_stock(
            store_ids=["STORE_TLV_01"],
            in_stock_only=True,
            limit=10
        )
        assert "medications" in result
        # All returned medications should have stock
        for med in result["medications"]:
            if med["stock"]:
                assert any(s["status"] == "in_stock" for s in med["stock"])
    
    def test_query_multiple_stores(self):
        """Test querying across multiple stores."""
        result = query_medications_with_stock(
            store_ids=["STORE_TLV_01", "STORE_JLM_01"],
            limit=10
        )
        assert "medications" in result
        # Check stock info includes multiple stores
        for med in result["medications"]:
            store_ids = [s["store_id"] for s in med["stock"]]
            assert len(set(store_ids)) <= 2  # Should have at most 2 stores


class TestQueryStockMultipleStores:
    """Tests for query_stock_multiple_stores tool."""
    
    def test_query_by_med_id(self):
        """Test querying stock by medication ID."""
        result = query_stock_multiple_stores(med_id="MED001")
        assert "med_id" in result
        assert "stock" in result
        assert isinstance(result["stock"], list)
    
    def test_query_by_med_name(self):
        """Test querying stock by medication name."""
        result = query_stock_multiple_stores(med_name="Nurofen")
        assert "med_id" in result
        assert "stock" in result
    
    def test_query_specific_stores(self):
        """Test querying stock for specific stores."""
        result = query_stock_multiple_stores(
            med_id="MED001",
            store_ids=["STORE_TLV_01"]
        )
        assert "stock" in result
        for stock_item in result["stock"]:
            assert stock_item["store_id"] == "STORE_TLV_01"
    
    def test_query_in_stock_only(self):
        """Test filtering to only in-stock stores."""
        result = query_stock_multiple_stores(
            med_id="MED001",
            in_stock_only=True
        )
        assert "stock" in result
        for stock_item in result["stock"]:
            assert stock_item["status"] == "in_stock"
    
    def test_medication_not_found(self):
        """Test handling of non-existent medication."""
        result = query_stock_multiple_stores(med_name="NonExistentMed")
        assert "error" in result
        assert result["error"] == "MEDICATION_NOT_FOUND"
    
    def test_missing_parameters(self):
        """Test error when no parameters provided."""
        result = query_stock_multiple_stores()
        assert "error" in result
        assert result["error"] == "MISSING_PARAMETER"


class TestListStores:
    """Tests for list_stores tool."""
    
    def test_list_all_stores(self):
        """Test listing all stores."""
        result = list_stores()
        assert "stores" in result
        assert "count" in result
        assert result["count"] > 0
    
    def test_filter_by_city(self):
        """Test filtering stores by city."""
        result = list_stores(city="Tel Aviv")
        assert "stores" in result
        for store in result["stores"]:
            assert "tel aviv" in store["city"].lower()
    
    def test_filter_by_city_no_match(self):
        """Test filtering by city with no matches."""
        result = list_stores(city="NonExistentCity")
        assert "stores" in result
        assert result["count"] == 0


class TestQueryPrescriptionsFlexible:
    """Tests for query_prescriptions_flexible tool."""
    
    def test_query_by_user_id(self):
        """Test querying prescriptions by user ID."""
        result = query_prescriptions_flexible(user_id="1003", limit=10)
        assert "prescriptions" in result
        for rx in result["prescriptions"]:
            assert rx["user_id"] == "1003"
    
    def test_query_by_med_id(self):
        """Test querying prescriptions by medication ID."""
        result = query_prescriptions_flexible(med_id="MED003", limit=10)
        assert "prescriptions" in result
        for rx in result["prescriptions"]:
            assert rx["med_id"] == "MED003"
    
    def test_query_by_med_name(self):
        """Test querying prescriptions by medication name."""
        result = query_prescriptions_flexible(med_name="Lipitor", limit=10)
        assert "prescriptions" in result
    
    def test_query_expiring_soon(self):
        """Test querying prescriptions expiring soon."""
        result = query_prescriptions_flexible(expiring_soon_days=60, limit=10)
        assert "prescriptions" in result
        for rx in result["prescriptions"]:
            assert "status" in rx
            assert rx["status"] in ["expired", "active", "no_refills"]
    
    def test_query_has_refills(self):
        """Test filtering by refill availability."""
        result = query_prescriptions_flexible(has_refills=True, limit=10)
        assert "prescriptions" in result
        for rx in result["prescriptions"]:
            assert rx["refills_remaining"] > 0
    
    def test_query_no_refills(self):
        """Test filtering for prescriptions with no refills."""
        result = query_prescriptions_flexible(has_refills=False, limit=10)
        assert "prescriptions" in result
        for rx in result["prescriptions"]:
            assert rx["refills_remaining"] <= 0
    
    def test_medication_not_found(self):
        """Test handling of non-existent medication name."""
        result = query_prescriptions_flexible(med_name="NonExistentMed")
        assert "error" in result
        assert result["error"] == "MEDICATION_NOT_FOUND"


class TestRequestPrescriptionRefill:
    """Tests for request_prescription_refill tool."""
    
    def test_refill_valid_prescription(self):
        """Test refilling a valid prescription."""
        # First, get a prescription that has refills
        rx_list = list_user_prescriptions("1003")
        if not rx_list["prescriptions"]:
            pytest.skip("No prescriptions found for user 1003")
        
        # Find a prescription with refills remaining
        rx_with_refills = None
        for rx in rx_list["prescriptions"]:
            if rx["refills_remaining"] > 0:
                rx_with_refills = rx
                break
        
        if not rx_with_refills:
            pytest.skip("No prescriptions with refills remaining for user 1003")
        
        # Get original refills count
        original_refills = rx_with_refills["refills_remaining"]
        
        # Clean up any existing refill requests for this prescription to avoid unique constraint violation
        from app.db import exec_sql
        try:
            exec_sql(
                "DELETE FROM refill_requests WHERE prescription_id = %s",
                (rx_with_refills["prescription_id"],)
            )
        except Exception:
            pass  # Ignore errors in cleanup
        
        result = request_prescription_refill("1003", rx_with_refills["prescription_id"])
        
        # Should succeed
        assert result["accepted"] is True, f"Refill request failed: {result}"
        assert "refill_request_id" in result
        assert result["status"] == "submitted"
        
        # Verify refills decreased
        rx_after = list_user_prescriptions("1003")
        rx_updated = next(
            (r for r in rx_after["prescriptions"] if r["prescription_id"] == rx_with_refills["prescription_id"]),
            None
        )
        if rx_updated:
            assert rx_updated["refills_remaining"] == original_refills - 1, \
                f"Expected refills to decrease from {original_refills} to {original_refills - 1}, got {rx_updated['refills_remaining']}"
    
    def test_refill_not_found(self):
        """Test refilling non-existent prescription."""
        result = request_prescription_refill("1001", "RX-9999")
        assert result["accepted"] is False
        assert result["error"] == "NOT_FOUND"
    
    def test_refill_unauthorized(self):
        """Test refilling prescription for wrong user."""
        rx_list = list_user_prescriptions("1003")
        if rx_list["prescriptions"]:
            rx = rx_list["prescriptions"][0]
            result = request_prescription_refill("1001", rx["prescription_id"])
            assert result["accepted"] is False
            assert result["error"] == "UNAUTHORIZED"
    
    def test_refill_no_refills_remaining(self):
        """Test refilling prescription with no refills."""
        # Find a prescription with no refills
        rx_list = query_prescriptions_flexible(has_refills=False, limit=1)
        if rx_list["prescriptions"]:
            rx = rx_list["prescriptions"][0]
            result = request_prescription_refill(rx["user_id"], rx["prescription_id"])
            assert result["accepted"] is False
            assert result["error"] == "NO_REFILLS"


class TestRunTool:
    """Tests for run_tool wrapper function."""
    
    def test_run_existing_tool(self):
        """Test running an existing tool."""
        result = run_tool("get_medication_by_name", {"name": "Nurofen"})
        assert "found" in result
    
    def test_run_nonexistent_tool(self):
        """Test running a non-existent tool."""
        result = run_tool("non_existent_tool", {})
        assert "error" in result
        assert result["error"] == "UNKNOWN_TOOL"
    
    def test_run_tool_with_invalid_args(self):
        """Test running tool with invalid arguments."""
        # This should handle gracefully and return an error
        result = run_tool("get_medication_by_name", {})
        # Should return error for missing required parameter
        assert result is not None
        assert "error" in result
        assert result["error"] == "MISSING_REQUIRED_ARGUMENT"


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_string_search(self):
        """Test handling of empty string searches."""
        result = list_medications(search_term="", limit=10)
        assert "medications" in result
    
    def test_very_large_limit(self):
        """Test handling of very large limit."""
        result = list_medications(limit=10000)
        assert "medications" in result
    
    def test_special_characters_in_search(self):
        """Test handling of special characters in search."""
        result = get_medication_by_name("Test@#$%")
        assert "found" in result
    
    def test_none_values_handling(self):
        """Test that None values are handled properly."""
        result = query_medications_flexible(
            brand_name=None,
            generic_name=None,
            limit=10
        )
        assert "medications" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

