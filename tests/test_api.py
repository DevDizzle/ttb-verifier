import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# 1. Mock the AI response so we don't hit Google's API during tests
MOCK_GEMINI_RESPONSE = {
    "brand_name": {"match": True, "found_value": "Old Tom", "reason": "Exact match"},
    "product_type": {"match": True, "found_value": "Bourbon", "reason": "Match"},
    "abv": {"match": True, "found_value": "45%", "reason": "Match"},
    "net_contents": {"match": True, "found_value": "750ml", "reason": "Match"},
    "government_warning": {"present": True, "found_text_snippet": "Surgeon General..."},
    "overall_match": True
}

# 2. The Test Function
@patch("app.main.analyze_label_with_gemini")  # <--- MAGIC: Replaces the real function
def test_verify_endpoint_success(mock_ai):
    # Tell the mock what to return when called
    mock_ai.return_value = MOCK_GEMINI_RESPONSE

    # Simulate a file upload
    # Using the existing sample file
    with open("samples/old_tom_distillery.jpg", "rb") as f:
        response = client.post(
            "/verify",
            data={
                "brand_name": "Old Tom",
                "product_type": "Bourbon",
                "abv": "45%",
                "net_contents": "750ml"
            },
            files={"file": ("old_tom_distillery.jpg", f, "image/jpeg")}
        )

    # 3. Assertions (The Verification)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["overall_match"] is True
    assert json_data["brand_name"]["match"] is True
