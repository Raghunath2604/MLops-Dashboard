"""
Integration tests for multi-tenant isolation
Tests that organizations cannot access each other's data
"""

import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def test_multitenancy():
    """
    Test multi-tenant data isolation:
    1. Register user1 and get API key
    2. Register user2 and get API key
    3. User1 makes predictions
    4. User2 makes predictions
    5. Verify user1 CANNOT see user2's predictions
    6. Verify user2 CANNOT see user1's predictions
    """

    async with httpx.AsyncClient(timeout=30) as client:
        print("=" * 60)
        print("MULTI-TENANT ISOLATION TEST")
        print("=" * 60)

        # Step 1: Register User 1
        print("\n[1] Registering User 1...")
        user1_response = await client.post(
            f"{BASE_URL}/auth/register",
            params={"username": "tenant_user_1", "password": "test123"}
        )
        user1_data = user1_response.json()
        user1_api_key = user1_data.get("api_key")
        user1_org = user1_data.get("organization")
        print(f"✓ User 1 registered")
        print(f"  - API Key: {user1_api_key[:20]}...")
        print(f"  - Organization: {user1_org}")

        # Step 2: Register User 2
        print("\n[2] Registering User 2...")
        user2_response = await client.post(
            f"{BASE_URL}/auth/register",
            params={"username": "tenant_user_2", "password": "test123"}
        )
        user2_data = user2_response.json()
        user2_api_key = user2_data.get("api_key")
        user2_org = user2_data.get("organization")
        print(f"✓ User 2 registered")
        print(f"  - API Key: {user2_api_key[:20]}...")
        print(f"  - Organization: {user2_org}")

        # Verify they have different orgs
        assert user1_org != user2_org, "ERROR: Users should have different organizations!"
        print(f"✓ Organizations are different (GOOD)")

        # Step 3: User 1 makes predictions
        print("\n[3] User 1 making predictions...")
        user1_headers = {"Authorization": f"Bearer {user1_api_key}"}

        pred1_response = await client.get(
            f"{BASE_URL}/predict",
            params={"text": "This is a great product! I love it"},
            headers=user1_headers
        )
        pred1_data = pred1_response.json()
        print(f"✓ User 1 prediction 1: {pred1_data['prediction']} ({pred1_data['confidence']:.2%})")

        pred2_response = await client.get(
            f"{BASE_URL}/predict",
            params={"text": "This product is terrible and doesn't work"},
            headers=user1_headers
        )
        pred2_data = pred2_response.json()
        print(f"✓ User 1 prediction 2: {pred2_data['prediction']} ({pred2_data['confidence']:.2%})")

        # Step 4: User 2 makes predictions
        print("\n[4] User 2 making predictions...")
        user2_headers = {"Authorization": f"Bearer {user2_api_key}"}

        pred3_response = await client.get(
            f"{BASE_URL}/predict",
            params={"text": "Excellent service, highly recommended"},
            headers=user2_headers
        )
        pred3_data = pred3_response.json()
        print(f"✓ User 2 prediction 1: {pred3_data['prediction']} ({pred3_data['confidence']:.2%})")

        pred4_response = await client.get(
            f"{BASE_URL}/predict",
            params={"text": "Worst experience ever"},
            headers=user2_headers
        )
        pred4_data = pred4_response.json()
        print(f"✓ User 2 prediction 2: {pred4_data['prediction']} ({pred4_data['confidence']:.2%})")

        # Step 5: Verify User 1 can only see their own predictions
        print("\n[5] Verifying User 1's data isolation...")
        user1_predictions_response = await client.get(
            f"{BASE_URL}/predictions?limit=100",
            headers=user1_headers
        )
        user1_predictions = user1_predictions_response.json()
        user1_count = user1_predictions["total"]
        print(f"✓ User 1 sees {user1_count} predictions")

        # User 1 should see exactly 2 predictions (their own)
        assert user1_count == 2, f"ERROR: User 1 should see 2 predictions, got {user1_count}"
        print(f"✓ User 1 sees exactly 2 predictions (CORRECT)")

        # Verify texts match
        texts = [p["input_text"] for p in user1_predictions["predictions"]]
        assert "This is a great product! I love it" in texts
        assert "This product is terrible and doesn't work" in texts
        print(f"✓ User 1's predictions contain only their own data (GOOD)")

        # Step 6: Verify User 2 can only see their own predictions
        print("\n[6] Verifying User 2's data isolation...")
        user2_predictions_response = await client.get(
            f"{BASE_URL}/predictions?limit=100",
            headers=user2_headers
        )
        user2_predictions = user2_predictions_response.json()
        user2_count = user2_predictions["total"]
        print(f"✓ User 2 sees {user2_count} predictions")

        # User 2 should see exactly 2 predictions (their own)
        assert user2_count == 2, f"ERROR: User 2 should see 2 predictions, got {user2_count}"
        print(f"✓ User 2 sees exactly 2 predictions (CORRECT)")

        # Verify texts match
        texts = [p["input_text"] for p in user2_predictions["predictions"]]
        assert "Excellent service, highly recommended" in texts
        assert "Worst experience ever" in texts
        print(f"✓ User 2's predictions contain only their own data (GOOD)")

        # Step 7: Verify User 1 CANNOT see User 2's predictions
        print("\n[7] Verifying USER 1 CANNOT see USER 2's data...")
        user1_texts = [p["input_text"] for p in user1_predictions["predictions"]]
        assert "Excellent service, highly recommended" not in user1_texts
        assert "Worst experience ever" not in user1_texts
        print(f"✓ User 1 cannot access User 2's predictions (SECURE)")

        # Step 8: Verify User 2 CANNOT see User 1's predictions
        print("\n[8] Verifying USER 2 CANNOT see USER 1's data...")
        user2_texts = [p["input_text"] for p in user2_predictions["predictions"]]
        assert "This is a great product! I love it" not in user2_texts
        assert "This product is terrible and doesn't work" not in user2_texts
        print(f"✓ User 2 cannot access User 1's predictions (SECURE)")

        # Step 9: Test metrics isolation
        print("\n[9] Verifying metrics isolation...")
        user1_metrics = await client.get(
            f"{BASE_URL}/model-metrics",
            headers=user1_headers
        )
        user1_metrics_data = user1_metrics.json()
        print(f"✓ User 1 metrics - Total: {user1_metrics_data['total']}, Avg Confidence: {user1_metrics_data['avg_confidence']:.4f}")

        user2_metrics = await client.get(
            f"{BASE_URL}/model-metrics",
            headers=user2_headers
        )
        user2_metrics_data = user2_metrics.json()
        print(f"✓ User 2 metrics - Total: {user2_metrics_data['total']}, Avg Confidence: {user2_metrics_data['avg_confidence']:.4f}")

        assert user1_metrics_data['total'] == 2
        assert user2_metrics_data['total'] == 2
        print(f"✓ Metrics are isolated per organization (GOOD)")

        # Step 10: Test authentication enforcement
        print("\n[10] Testing authentication enforcement...")
        no_auth_response = await client.get(f"{BASE_URL}/predict?text=test")
        print(f"✓ Request without auth: Status {no_auth_response.status_code}")
        assert no_auth_response.status_code == 401, "Should reject unauthenticated requests"
        print(f"✓ Unauthenticated requests are rejected (SECURE)")

        # Step 11: Test invalid API key rejection
        print("\n[11] Testing invalid API key rejection...")
        invalid_headers = {"Authorization": "Bearer invalid_key_12345"}
        invalid_response = await client.get(
            f"{BASE_URL}/predict?text=test",
            headers=invalid_headers
        )
        print(f"✓ Request with invalid key: Status {invalid_response.status_code}")
        assert invalid_response.status_code == 401, "Should reject invalid API keys"
        print(f"✓ Invalid API keys are rejected (SECURE)")

        print("\n" + "=" * 60)
        print("✅ ALL MULTI-TENANT ISOLATION TESTS PASSED!")
        print("=" * 60)
        print("\nKey Results:")
        print(f"  - ✓ Users have separate organizations")
        print(f"  - ✓ User data is completely isolated")
        print(f"  - ✓ No cross-organization data leakage")
        print(f"  - ✓ Metrics are per-organization")
        print(f"  - ✓ Authentication is enforced")
        print(f"  - ✓ Invalid credentials are rejected")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_multitenancy())
