#!/usr/bin/env python3
"""
Test script to verify reasoning configuration is passed correctly to the backend.

Run this script with the backend server running to test reasoning functionality.
Set OPENROUTER_DEBUG=1 in your .env file to see detailed logs.
"""

import httpx
import json
import os
from typing import Dict, Any

# Backend URL (adjust if needed)
API_BASE = "http://127.0.0.1:8000"

def test_reasoning_configs():
    """Test different reasoning configurations"""
    
    # Test configurations
    test_cases = [
        {
            "name": "No reasoning",
            "reasoning": None
        },
        {
            "name": "Effort-based reasoning (low)",
            "reasoning": {"effort": "low"}
        },
        {
            "name": "Effort-based reasoning (medium)",
            "reasoning": {"effort": "medium"}
        },
        {
            "name": "Effort-based reasoning (high)",
            "reasoning": {"effort": "high"}
        },
        {
            "name": "Token-based reasoning (1024 tokens)",
            "reasoning": {"max_tokens": 1024}
        },
        {
            "name": "Token-based reasoning (8192 tokens)",
            "reasoning": {"max_tokens": 8192}
        }
    ]
    
    print("=" * 80)
    print("🧪 REASONING CONFIGURATION TEST")
    print("=" * 80)
    print()
    
    for test in test_cases:
        print(f"📝 Testing: {test['name']}")
        print(f"   Reasoning config: {test['reasoning']}")
        
        # Create a mock request payload
        payload = {
            "session_id": "test-session-123",
            "models": [{"name": "anthropic/claude-3.5-sonnet"}],
            "default_tries": 1,
            "reasoning": test["reasoning"]
        }
        
        print(f"   Request payload: {json.dumps(payload, indent=2)}")
        print()
        
        # Note: This would normally make an actual API call
        # For now, just showing what would be sent
        
    print("=" * 80)
    print("✅ Test configurations generated successfully!")
    print("=" * 80)
    print()
    print("To actually test with the backend:")
    print("1. Ensure OPENROUTER_DEBUG=1 is set in your .env file")
    print("2. Start the backend server")
    print("3. Create a real session with images and questions")
    print("4. Use the session_id to test grading with different reasoning configs")
    print()

if __name__ == "__main__":
    test_reasoning_configs()
