#!/usr/bin/env python3
"""
Create virtual layers using filters instead of separate tables
"""

import asyncio
import asyncpg

async def create_virtual_layers():
    """Create virtual TMS layers with filters"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="postgres",
        password="postgres",
        database="gis_backend"
    )
    
    try:
        print("🎯 ایجاد لایه‌های مجازی")
        print("=" * 30)
        
        # Define layer configurations
        layers = [
            {
                "name": "beacons",
                "title": "فانوس‌های دریایی",
                "table_name": "my_points",
                "filter": None,  # No filter for points
                "description": "فانوس‌های دریایی و علائم ناوبری"
            },
            {
                "name": "residential_roads",
                "title": "جاده‌های مسکونی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'residential'",
                "description": "جاده‌های مسکونی و محلی"
            },
            {
                "name": "primary_roads",
                "title": "جاده‌های اصلی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'primary'",
                "description": "جاده‌های اصلی و شریانی"
            },
            {
                "name": "secondary_roads",
                "title": "جاده‌های فرعی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'secondary'",
                "description": "جاده‌های فرعی"
            },
            {
                "name": "tertiary_roads",
                "title": "جاده‌های محلی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'tertiary'",
                "description": "جاده‌های محلی و دسترسی"
            },
            {
                "name": "trunk_roads",
                "title": "جاده‌های شریانی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'trunk'",
                "description": "جاده‌های شریانی"
            },
            {
                "name": "motorway_roads",
                "title": "اتوبان‌ها",
                "table_name": "turkaman_map",
                "filter": "fclass = 'motorway'",
                "description": "اتوبان‌ها و بزرگراه‌ها"
            },
            {
                "name": "tracks",
                "title": "مسیرهای خاکی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'track'",
                "description": "مسیرهای خاکی و غیرآسفالت"
            },
            {
                "name": "footways",
                "title": "پیاده‌روها",
                "table_name": "turkaman_map",
                "filter": "fclass = 'footway'",
                "description": "پیاده‌روها و مسیرهای پیاده"
            },
            {
                "name": "service_roads",
                "title": "جاده‌های خدماتی",
                "table_name": "turkaman_map",
                "filter": "fclass = 'service'",
                "description": "جاده‌های خدماتی و دسترسی"
            }
        ]
        
        # Clear existing layers
        print("🗑️ حذف لایه‌های قبلی...")
        await conn.execute("DELETE FROM tms_layers")
        
        # Create virtual layers
        for layer in layers:
            print(f"🔄 ایجاد لایه: {layer['title']}")
            
            # Get feature count with filter
            if layer['filter']:
                count_query = f"SELECT COUNT(*) FROM {layer['table_name']} WHERE {layer['filter']}"
            else:
                count_query = f"SELECT COUNT(*) FROM {layer['table_name']}"
            
            feature_count = await conn.fetchval(count_query)
            
            # Get bounds
            if layer['filter']:
                bounds_query = f"""
                    SELECT 
                        ST_XMin(ST_Extent(geom)) as minx,
                        ST_YMin(ST_Extent(geom)) as miny,
                        ST_XMax(ST_Extent(geom)) as maxx,
                        ST_YMax(ST_Extent(geom)) as maxy
                    FROM {layer['table_name']} 
                    WHERE {layer['filter']} AND geom IS NOT NULL
                """
            else:
                bounds_query = f"""
                    SELECT 
                        ST_XMin(ST_Extent(geom)) as minx,
                        ST_YMin(ST_Extent(geom)) as miny,
                        ST_XMax(ST_Extent(geom)) as maxx,
                        ST_YMax(ST_Extent(geom)) as maxy
                    FROM {layer['table_name']} 
                    WHERE geom IS NOT NULL
                """
            
            bounds_result = await conn.fetchrow(bounds_query)
            
            if bounds_result and bounds_result['minx'] is not None:
                bounds = {
                    "minx": float(bounds_result['minx']),
                    "miny": float(bounds_result['miny']),
                    "maxx": float(bounds_result['maxx']),
                    "maxy": float(bounds_result['maxy'])
                }
                center = {
                    "lat": (bounds['miny'] + bounds['maxy']) / 2,
                    "lng": (bounds['minx'] + bounds['maxx']) / 2
                }
            else:
                bounds = None
                center = None
            
            # Insert layer
            insert_query = """
                INSERT INTO tms_layers (
                    name, title, description, table_name, 
                    min_zoom, max_zoom, bounds, center, crs, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            await conn.execute(
                insert_query,
                layer['name'],
                layer['title'],
                layer['description'],
                layer['table_name'],
                0,  # min_zoom
                18, # max_zoom
                json.dumps(bounds) if bounds else None,
                json.dumps(center) if center else None,
                'EPSG:4326',
                True
            )
            
            print(f"  ✅ {layer['title']}: {feature_count} مورد")
        
        print("\n🎉 لایه‌های مجازی ایجاد شدند!")
        
        # Show summary
        summary_query = """
            SELECT name, title, table_name, 
                   (bounds->>'minx')::float as minx,
                   (bounds->>'maxx')::float as maxx,
                   (bounds->>'miny')::float as miny,
                   (bounds->>'maxy')::float as maxy
            FROM tms_layers 
            ORDER BY name
        """
        
        layers_data = await conn.fetch(summary_query)
        
        print(f"\n📋 خلاصه لایه‌ها ({len(layers_data)} لایه):")
        print("=" * 50)
        
        for layer in layers_data:
            bounds_info = ""
            if layer['minx'] is not None:
                bounds_info = f" (محدوده: {layer['minx']:.2f}, {layer['miny']:.2f} تا {layer['maxx']:.2f}, {layer['maxy']:.2f})"
            
            print(f"  - {layer['title']} ({layer['name']})")
            print(f"    جدول: {layer['table_name']}{bounds_info}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    import json
    asyncio.run(create_virtual_layers())
