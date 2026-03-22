#!/usr/bin/env python3
"""Simple test script to verify chatbot is working."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"✓ Health: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health failed: {e}")
        return False

def test_create_session():
    """Test creating a chat session."""
    print("\nTesting create session endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/chatbot/sessions",
            headers={"Content-Type": "application/json"},
            json={},
            timeout=5
        )
        print(f"✓ Create session: {response.status_code}")
        data = response.json()
        print(f"  Session ID: {data.get('session_id')}")
        return data.get('session_id')
    except Exception as e:
        print(f"✗ Create session failed: {e}")
        return None

def test_send_message(session_id):
    """Test sending a message."""
    print(f"\nTesting send message endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/chatbot/sessions/{session_id}/messages",
            headers={"Content-Type": "application/json"},
            json={"message": "hello"},
            timeout=5
        )
        print(f"✓ Send message: {response.status_code}")
        data = response.json()
        print(f"  Response: {data.get('content', 'No content')[:100]}")
        return True
    except Exception as e:
        print(f"✗ Send message failed: {e}")
        return False

def test_get_history(session_id):
    """Test getting chat history."""
    print(f"\nTesting get history endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/chatbot/sessions/{session_id}/history",
            timeout=5
        )
        print(f"✓ Get history: {response.status_code}")
        data = response.json()
        print(f"  Messages: {len(data)}")
        return True
    except Exception as e:
        print(f"✗ Get history failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CloudForge Chatbot - Simple Test")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\n✗ Flask app is not responding!")
        sys.exit(1)
    
    # Test create session
    session_id = test_create_session()
    if not session_id:
        print("\n✗ Could not create session!")
        sys.exit(1)
    
    # Test send message
    if not test_send_message(session_id):
        print("\n✗ Could not send message!")
        sys.exit(1)
    
    # Test get history
    if not test_get_history(session_id):
        print("\n✗ Could not get history!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
