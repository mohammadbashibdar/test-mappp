#!/usr/bin/env python3
"""
Simple test script for layer management API using urllib
"""

import urllib.request
import urllib.parse
import json

API_BASE = "http://localhost:8000/api/v1"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint"""
    url = f"{API_BASE}{endpoint}"
    
    try:
        if method == "GET":
            with urllib.request.urlopen(url) as response:
                result = json.loads(response.read().decode())
                return result, response.status
        elif method == "POST":
            if data:
                data = json.dumps(data).encode()
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url, method=method)
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                return result, response.status
    except Exception as e:
        return None, str(e)

def main():
    print("🗺️ Testing Layer Management API")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    result, status = test_endpoint("/database/health")
    if status == 200:
        print(f"✅ Health check: {result['status']}")
    else:
        print(f"❌ Health check failed: {status}")
        return
    
    # Test 2: Discover layers
    print("\n2. Testing layer discovery...")
    result, status = test_endpoint("/database/layers/discover")
    if status == 200:
        print(f"✅ Discovery successful:")
        print(f"   - Total tables: {result['total_tables']}")
        print(f"   - Existing layers: {result['existing_layers']}")
        print(f"   - Ready for layers: {result['ready_for_layers']}")
        
        if result['suggestions']:
            print("   - Table suggestions:")
            for suggestion in result['suggestions']:
                status_text = "Ready" if suggestion['is_ready_for_layer'] else "Has Layer" if suggestion['has_existing_layer'] else "Empty"
                print(f"     * {suggestion['table_name']}: {status_text} ({suggestion['feature_count']} features)")
    else:
        print(f"❌ Discovery failed: {status}")
    
    # Test 3: List layers
    print("\n3. Testing layer listing...")
    result, status = test_endpoint("/database/layers")
    if status == 200:
        print(f"✅ Found {len(result)} existing layers")
        for layer in result:
            print(f"   - {layer['name']} (ID: {layer['id']})")
    else:
        print(f"❌ Layer listing failed: {status}")
    
    # Test 4: List tables
    print("\n4. Testing table listing...")
    result, status = test_endpoint("/database/tables")
    if status == 200:
        print(f"✅ Found {len(result)} tables:")
        for table in result:
            print(f"   - {table['name']} ({table['type']})")
    else:
        print(f"❌ Table listing failed: {status}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
