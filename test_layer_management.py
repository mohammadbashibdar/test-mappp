#!/usr/bin/env python3
"""
Test script for layer management functionality
This script demonstrates how to use the new layer discovery and management APIs
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

API_BASE = "http://localhost:8000/api/v1"

async def test_layer_discovery():
    """Test the layer discovery functionality"""
    print("🔍 Testing Layer Discovery...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE}/database/layers/discover") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Found {data['total_tables']} tables")
                    print(f"✅ {data['existing_layers']} existing layers")
                    print(f"✅ {data['ready_for_layers']} ready for layer creation")
                    
                    print("\n📋 Table Suggestions:")
                    for suggestion in data['suggestions']:
                        status = "✅ Ready" if suggestion['is_ready_for_layer'] else "⚠️ Has Layer" if suggestion['has_existing_layer'] else "❌ Empty"
                        print(f"  - {suggestion['table_name']}: {status} ({suggestion['feature_count']} features)")
                    
                    return data
                else:
                    print(f"❌ Error: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def test_create_layer(table_name: str):
    """Test creating a layer from a table"""
    print(f"\n➕ Creating layer from table: {table_name}")
    
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "table_name": table_name,
                "layer_name": f"layer_{table_name}",
                "title": f"Test Layer {table_name}"
            }
            
            async with session.post(
                f"{API_BASE}/database/tables/{table_name}/create-layer",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Layer created successfully: {data['name']} (ID: {data['id']})")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Error creating layer: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def test_list_layers():
    """Test listing all layers"""
    print("\n📋 Listing all layers...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE}/database/layers") as response:
                if response.status == 200:
                    layers = await response.json()
                    print(f"✅ Found {len(layers)} layers:")
                    for layer in layers:
                        print(f"  - {layer['name']} (ID: {layer['id']}) - {layer['table_name']}")
                    return layers
                else:
                    print(f"❌ Error: {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

async def test_layer_info(layer_id: int):
    """Test getting detailed layer information"""
    print(f"\nℹ️ Getting info for layer {layer_id}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE}/database/layers/{layer_id}/info") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Layer info retrieved:")
                    print(f"  - Name: {data['layer']['name']}")
                    print(f"  - Table: {data['layer']['table_name']}")
                    print(f"  - Zoom: {data['layer']['min_zoom']}-{data['layer']['max_zoom']}")
                    print(f"  - CRS: {data['layer']['crs']}")
                    print(f"  - Tile URL: {data['tile_url_template']}")
                    return data
                else:
                    print(f"❌ Error: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def test_bulk_create(table_names: list):
    """Test bulk layer creation"""
    print(f"\n🚀 Bulk creating layers from {len(table_names)} tables...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE}/database/layers/bulk-create",
                json=table_names
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bulk creation completed:")
                    print(f"  - Created: {data['total_created']}")
                    print(f"  - Errors: {len(data['errors'])}")
                    if data['errors']:
                        print("  - Error details:")
                        for error in data['errors']:
                            print(f"    * {error}")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def main():
    """Main test function"""
    print("🗺️ GIS Layer Management Test")
    print("=" * 50)
    
    # Test 1: Discover layers
    discovery_data = await test_layer_discovery()
    if not discovery_data:
        print("❌ Cannot proceed without discovery data")
        return
    
    # Test 2: List existing layers
    existing_layers = await test_list_layers()
    
    # Test 3: Create a single layer (if there are ready tables)
    ready_tables = [s for s in discovery_data['suggestions'] if s['is_ready_for_layer'] and not s['has_existing_layer']]
    if ready_tables:
        test_table = ready_tables[0]['table_name']
        created_layer = await test_create_layer(test_table)
        
        if created_layer:
            # Test 4: Get layer info
            await test_layer_info(created_layer['id'])
    
    # Test 5: Bulk create (if there are multiple ready tables)
    if len(ready_tables) > 1:
        table_names = [t['table_name'] for t in ready_tables[:3]]  # Limit to 3 for testing
        await test_bulk_create(table_names)
    
    # Test 6: Final layer list
    print("\n📋 Final layer list:")
    await test_list_layers()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
