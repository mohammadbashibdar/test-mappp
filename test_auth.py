#!/usr/bin/env python3
"""
Test script for authentication system
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Test user registration"""
    print("Testing user registration...")
    
    register_data = {
        "name": "احمد محمدی",
        "mobile_number": "09123456789",
        "password": "123456",
        "email": "ahmad@example.com",
        "national_code": "1234567890"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_login():
    """Test user login"""
    print("\nTesting user login...")
    
    login_data = {
        "mobile_number": "09123456789",
        "password": "123456"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_get_current_user(token):
    """Test getting current user info"""
    if not token:
        print("No token available for testing current user")
        return
    
    print("\nTesting get current user...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    print("Starting authentication system tests...")
    print("=" * 50)
    
    # Test health endpoint first
    test_health()
    
    # Test registration
    register_response = test_register()
    
    # Test login
    token = test_login()
    
    # Test get current user
    test_get_current_user(token)
    
    print("\n" + "=" * 50)
    print("Tests completed!")
