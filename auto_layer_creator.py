#!/usr/bin/env python3
"""
Auto layer creator for new tables
"""

import asyncio
import asyncpg
import json

async def analyze_table_for_auto_layers(table_name):
    """Analyze a table to determine how to create layers automatically"""
    
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='gis_backend'
    )
    
    try:
        print(f"🔍 تحلیل جدول {table_name}...")
        
        # Get geometry type
        geom_type_query = f"""
            SELECT ST_GeometryType(geom) as geom_type
            FROM {table_name}
            WHERE geom IS NOT NULL
            LIMIT 1
        """
        
        geom_result = await conn.fetchrow(geom_type_query)
        geom_type = geom_result['geom_type'] if geom_result else None
        
        print(f"  نوع هندسه: {geom_type}")
        
        # For POINT tables - create single layer
        if geom_type and 'Point' in geom_type:
            print(f"  📍 جدول نقطه‌ای - ایجاد یک لایه")
            return [{
                "name": f"layer_{table_name}",
                "title": f"لایه {table_name}",
                "table_name": table_name,
                "filter_condition": None,
                "description": f"لایه نقطه‌ای {table_name}"
            }]
        
        # For LINE/POLYGON tables - analyze fclass column
        elif geom_type and ('Line' in geom_type or 'Polygon' in geom_type):
            print(f"  📏 جدول خط/پلیگون - تحلیل فیلدهای فیلتر...")
            
            # Check for common filter columns
            filter_columns = ['fclass', 'type', 'category', 'class', 'highway', 'waterway', 'landuse']
            
            for col in filter_columns:
                # Check if column exists
                col_check_query = f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND column_name = '{col}'
                """
                
                col_exists = await conn.fetchrow(col_check_query)
                
                if col_exists:
                    print(f"    ✅ فیلد {col} یافت شد")
                    
                    # Get unique values
                    values_query = f"""
                        SELECT {col}, COUNT(*) as count
                        FROM {table_name}
                        WHERE {col} IS NOT NULL
                        GROUP BY {col}
                        ORDER BY count DESC
                        LIMIT 20
                    """
                    
                    values = await conn.fetch(values_query)
                    
                    if len(values) > 1:
                        print(f"    📊 {len(values)} مقدار مختلف یافت شد:")
                        for val in values[:5]:  # Show first 5
                            print(f"      - {val[col]}: {val['count']} مورد")
                        
                        # Create layers for each value
                        layers = []
                        for val in values:
                            if val['count'] > 0:  # Only create layers with data
                                layer_name = f"layer_{table_name}_{val[col].lower().replace(' ', '_').replace('-', '_')}"
                                layers.append({
                                    "name": layer_name,
                                    "title": f"{val[col]} - {table_name}",
                                    "table_name": table_name,
                                    "filter_condition": f"{col} = '{val[col]}'",
                                    "description": f"لایه {val[col]} از {table_name} ({val['count']} مورد)"
                                })
                        
                        return layers
                    else:
                        print(f"    ❌ فقط یک مقدار در {col} - نیازی به تقسیم نیست")
                else:
                    print(f"    ❌ فیلد {col} یافت نشد")
            
            # If no filter columns found, create single layer
            print(f"  📄 هیچ فیلد فیلتر یافت نشد - ایجاد یک لایه")
            return [{
                "name": f"layer_{table_name}",
                "title": f"لایه {table_name}",
                "table_name": table_name,
                "filter_condition": None,
                "description": f"لایه {table_name}"
            }]
        
        else:
            print(f"  ❓ نوع هندسه نامشخص - ایجاد لایه پیش‌فرض")
            return [{
                "name": f"layer_{table_name}",
                "title": f"لایه {table_name}",
                "table_name": table_name,
                "filter_condition": None,
                "description": f"لایه {table_name}"
            }]
    
    finally:
        await conn.close()

async def create_auto_layers_for_table(table_name):
    """Create layers automatically for a table"""
    
    print(f"🚀 ایجاد خودکار لایه‌ها برای {table_name}")
    print("=" * 50)
    
    # Analyze table
    layers_config = await analyze_table_for_auto_layers(table_name)
    
    if not layers_config:
        print("❌ هیچ لایه‌ای ایجاد نشد")
        return
    
    # Create layers
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='gis_backend'
    )
    
    try:
        for layer_config in layers_config:
            print(f"🔄 ایجاد لایه: {layer_config['title']}")
            
            # Get feature count
            if layer_config['filter_condition']:
                count_query = f"SELECT COUNT(*) FROM {layer_config['table_name']} WHERE {layer_config['filter_condition']}"
            else:
                count_query = f"SELECT COUNT(*) FROM {layer_config['table_name']}"
            
            feature_count = await conn.fetchval(count_query)
            
            # Get bounds
            if layer_config['filter_condition']:
                bounds_query = f"""
                    SELECT 
                        ST_XMin(ST_Extent(geom)) as minx,
                        ST_YMin(ST_Extent(geom)) as miny,
                        ST_XMax(ST_Extent(geom)) as maxx,
                        ST_YMax(ST_Extent(geom)) as maxy
                    FROM {layer_config['table_name']} 
                    WHERE {layer_config['filter_condition']} AND geom IS NOT NULL
                """
            else:
                bounds_query = f"""
                    SELECT 
                        ST_XMin(ST_Extent(geom)) as minx,
                        ST_YMin(ST_Extent(geom)) as miny,
                        ST_XMax(ST_Extent(geom)) as maxx,
                        ST_YMax(ST_Extent(geom)) as maxy
                    FROM {layer_config['table_name']} 
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
                    name, title, description, table_name, filter_condition,
                    min_zoom, max_zoom, bounds, center, crs, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """
            
            await conn.execute(
                insert_query,
                layer_config['name'],
                layer_config['title'],
                layer_config['description'],
                layer_config['table_name'],
                layer_config['filter_condition'],
                0,  # min_zoom
                18, # max_zoom
                json.dumps(bounds) if bounds else None,
                json.dumps(center) if center else None,
                'EPSG:4326',
                True
            )
            
            print(f"  ✅ {layer_config['title']}: {feature_count} مورد")
        
        print(f"\n🎉 {len(layers_config)} لایه برای {table_name} ایجاد شد!")
        
    finally:
        await conn.close()

async def auto_create_layers_for_all_tables():
    """Auto create layers for all available tables"""
    
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='gis_backend'
    )
    
    try:
        # Get all geographic tables
        tables_query = """
            SELECT tablename
            FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename NOT IN ('tms_layers', 'tile_cache', 'layer_styles', 'spatial_ref_sys')
            ORDER BY tablename
        """
        
        tables = await conn.fetch(tables_query)
        
        print(f"🔍 {len(tables)} جدول جغرافیایی یافت شد")
        
        for table in tables:
            table_name = table['tablename']
            print(f"\n{'='*60}")
            await create_auto_layers_for_table(table_name)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Create layers for specific table
        table_name = sys.argv[1]
        asyncio.run(create_auto_layers_for_table(table_name))
    else:
        # Create layers for all tables
        asyncio.run(auto_create_layers_for_all_tables())
