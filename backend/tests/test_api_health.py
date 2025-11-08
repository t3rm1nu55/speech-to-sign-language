"""
Test health check endpoints
"""

import pytest
from datetime import datetime

def test_health_check(client):
    """Test main health check endpoint"""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "version" in data
    assert "processing_mode" in data
    assert "services" in data
    assert "timestamp" in data

def test_readiness_check(client):
    """Test Kubernetes readiness probe"""
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"

def test_liveness_check(client):
    """Test Kubernetes liveness probe"""
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "alive"

def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "version" in data
    assert "docs" in data
