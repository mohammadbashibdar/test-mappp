#!/usr/bin/env python3
"""
Update existing layers with filter conditions
"""

import asyncio
import asyncpg

async def update_filters():
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='gis_backend'
    )
    
    try:
        # Add filter_condition column
        await conn.execute('ALTER TABLE tms_layers ADD COLUMN IF NOT EXISTS filter_condition TEXT')
        print('✅ فیلد filter_condition اضافه شد')
        
        # Update existing layers with filters
        filters = {
            'beacons': None,
            'residential_roads': "fclass = 'residential'",
            'primary_roads': "fclass = 'primary'",
            'secondary_roads': "fclass = 'secondary'",
            'tertiary_roads': "fclass = 'tertiary'",
            'trunk_roads': "fclass = 'trunk'",
            'motorway_roads': "fclass = 'motorway'",
            'tracks': "fclass = 'track'",
            'footways': "fclass = 'footway'",
            'service_roads': "fclass = 'service'"
        }
        
        for name, filter_cond in filters.items():
            await conn.execute(
                'UPDATE tms_layers SET filter_condition = $1 WHERE name = $2',
                filter_cond, name
            )
            print(f'✅ فیلتر برای {name} اضافه شد')
        
        print('\n🎉 به‌روزرسانی تکمیل شد!')
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_filters())
