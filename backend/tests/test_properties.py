from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": TEST_SEED_ADMIN_EMAIL, "password": TEST_SEED_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_create_property_without_token_returns_401(client_with_full_stack):
    response = client_with_full_stack.post(
        "/api/properties",
        json={"title": "x", "property_type": "APARTMENT", "listing_type": "SALE",
              "price_amount": 1.0, "price_currency": "USD",
              "address_line": "1", "city": "x", "country_code": "US"},
    )
    assert response.status_code == 401


def test_create_property_with_non_admin_token_returns_403(
    client_with_full_stack, non_admin_token
):
    response = client_with_full_stack.post(
        "/api/properties",
        json={"title": "x", "property_type": "APARTMENT", "listing_type": "SALE",
              "price_amount": 1.0, "price_currency": "USD",
              "address_line": "1", "city": "x", "country_code": "US"},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 403


def test_list_properties_without_token_returns_401(client_with_full_stack):
    response = client_with_full_stack.get("/api/properties")
    assert response.status_code == 401


def test_list_properties_with_non_admin_token_returns_403(
    client_with_full_stack, non_admin_token
):
    response = client_with_full_stack.get(
        "/api/properties", headers=_auth(non_admin_token)
    )
    assert response.status_code == 403


def test_admin_round_trip_create_list_get_update_delete(
    client_with_full_stack, property_create_payload
):
    client = client_with_full_stack
    token = _login_admin(client)
    headers = _auth(token)

    create = client.post("/api/properties", json=property_create_payload, headers=headers)
    assert create.status_code == 201, create.text
    created = create.json()
    assert created["title"] == "Modern Test Property"
    assert created["status"] == "AVAILABLE"
    assert created["price_currency"] == "USD"
    assert created["amenities"] == ["parking", "pool"]
    assert [img["url"] for img in created["images"]] == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
    ]
    assert created["created_by"] is not None

    pid = created["id"]

    listed = client.get("/api/properties", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert any(item["id"] == pid for item in body["items"])

    filtered = client.get(
        "/api/properties",
        params={"city": "Testville", "min_price": 1000, "max_price": 2000},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == pid for item in filtered.json()["items"])

    got = client.get(f"/api/properties/{pid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["id"] == pid

    patched = client.patch(
        f"/api/properties/{pid}",
        json={"price_amount": 1750.0, "status": "RESERVED", "amenities": ["gym"]},
        headers=headers,
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["price_amount"] == 1750.0
    assert body["status"] == "RESERVED"
    assert body["amenities"] == ["gym"]
    assert body["updated_by"] == body["created_by"]

    images_only = client.patch(
        f"/api/properties/{pid}",
        json={"images": []},
        headers=headers,
    )
    assert images_only.status_code == 200
    assert images_only.json()["images"] == []

    deleted = client.delete(f"/api/properties/{pid}", headers=headers)
    assert deleted.status_code == 204

    after = client.get(f"/api/properties/{pid}", headers=headers)
    assert after.status_code == 404


def test_get_unknown_property_returns_404(client_with_full_stack):
    token = _login_admin(client_with_full_stack)
    response = client_with_full_stack.get(
        "/api/properties/999999", headers=_auth(token)
    )
    assert response.status_code == 404


def test_update_unknown_property_returns_404(client_with_full_stack):
    token = _login_admin(client_with_full_stack)
    response = client_with_full_stack.patch(
        "/api/properties/999999",
        json={"price_amount": 1.0},
        headers=_auth(token),
    )
    assert response.status_code == 404


def test_update_rejects_explicit_null_on_required_field(
    client_with_full_stack, property_create_payload
):
    client = client_with_full_stack
    token = _login_admin(client)
    create = client.post(
        "/api/properties", json=property_create_payload, headers=_auth(token)
    )
    assert create.status_code == 201
    pid = create.json()["id"]

    response = client.patch(
        f"/api/properties/{pid}",
        json={"city": None},
        headers=_auth(token),
    )
    assert response.status_code == 422
    body = response.json()
    assert any("city" in err.get("msg", "") for err in body["detail"])

    client.delete(f"/api/properties/{pid}", headers=_auth(token))


def test_delete_unknown_property_returns_404(client_with_full_stack):
    token = _login_admin(client_with_full_stack)
    response = client_with_full_stack.delete(
        "/api/properties/999999", headers=_auth(token)
    )
    assert response.status_code == 404


def test_create_rejects_invalid_property_type(
    client_with_full_stack, property_create_payload
):
    token = _login_admin(client_with_full_stack)
    payload = {**property_create_payload, "property_type": "NOT_A_TYPE"}
    response = client_with_full_stack.post(
        "/api/properties", json=payload, headers=_auth(token)
    )
    assert response.status_code == 422


def test_create_rejects_negative_price(
    client_with_full_stack, property_create_payload
):
    token = _login_admin(client_with_full_stack)
    payload = {**property_create_payload, "price_amount": -1.0}
    response = client_with_full_stack.post(
        "/api/properties", json=payload, headers=_auth(token)
    )
    assert response.status_code == 422


def test_create_rejects_oversized_title(
    client_with_full_stack, property_create_payload
):
    token = _login_admin(client_with_full_stack)
    payload = {**property_create_payload, "title": "x" * 201}
    response = client_with_full_stack.post(
        "/api/properties", json=payload, headers=_auth(token)
    )
    assert response.status_code == 422


def test_create_rejects_non_url_image(
    client_with_full_stack, property_create_payload
):
    token = _login_admin(client_with_full_stack)
    payload = {
        **property_create_payload,
        "images": [{"url": "not a url", "sort_order": 0}],
    }
    response = client_with_full_stack.post(
        "/api/properties", json=payload, headers=_auth(token)
    )
    assert response.status_code == 422


def test_create_normalizes_lowercase_currency(
    client_with_full_stack, property_create_payload
):
    token = _login_admin(client_with_full_stack)
    payload = {**property_create_payload, "price_currency": "usd"}
    response = client_with_full_stack.post(
        "/api/properties", json=payload, headers=_auth(token)
    )
    assert response.status_code == 201
    assert response.json()["price_currency"] == "USD"


def test_list_pagination_returns_correct_window(
    client_with_full_stack, property_create_payload
):
    client = client_with_full_stack
    token = _login_admin(client)
    headers = _auth(token)
    for i in range(3):
        client.post(
            "/api/properties",
            json={**property_create_payload, "title": f"Pagination Property {i}"},
            headers=headers,
        )
    response = client.get(
        "/api/properties",
        params={"limit": 2, "offset": 1},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
