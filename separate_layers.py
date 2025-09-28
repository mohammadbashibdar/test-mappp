#!/usr/bin/env python3
"""
Separate data into different layers based on their types
"""

import asyncio
import asyncpg
import json

async def separate_turkaman_data():
    """Separate turkaman_map data into different tables based on fclass"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="postgres",
        password="postgres",
        database="gis_backend"
    )
    
    try:
        print("🔧 شروع تقسیم‌بندی داده‌های turkaman_map")
        print("=" * 50)
        
        # Get all unique fclass values
        fclass_query = """
            SELECT DISTINCT fclass, COUNT(*) as count
            FROM turkaman_map 
            WHERE fclass IS NOT NULL
            GROUP BY fclass
            ORDER BY count DESC
        """
        
        fclass_rows = await conn.fetch(fclass_query)
        
        print(f"📊 {len(fclass_rows)} نوع خط مختلف یافت شد:")
        for row in fclass_rows:
            print(f"  - {row['fclass']}: {row['count']} مورد")
        print()
        
        # Create separate tables for each fclass
        for row in fclass_rows:
            fclass = row['fclass']
            count = row['count']
            
            # Create table name
            table_name = f"line_{fclass.lower().replace(' ', '_')}"
            
            print(f"🔄 ایجاد جدول {table_name} ({count} مورد)...")
            
            # Create table
            create_table_query = f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS
                SELECT * FROM turkaman_map 
                WHERE fclass = $1
            """
            
            await conn.execute(create_table_query, fclass)
            
            # Add spatial index
            add_index_query = f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_geom 
                ON {table_name} USING GIST (geom)
            """
            
            await conn.execute(add_index_query)
            
            # Verify count
            verify_query = f"SELECT COUNT(*) FROM {table_name}"
            actual_count = await conn.fetchval(verify_query)
            
            print(f"  ✅ جدول {table_name} ایجاد شد ({actual_count} مورد)")
        
        print("\n🎉 تقسیم‌بندی تکمیل شد!")
        
        # Show summary
        print("\n📋 خلاصه جداول ایجاد شده:")
        print("=" * 35)
        
        for row in fclass_rows:
            fclass = row['fclass']
            table_name = f"line_{fclass.lower().replace(' ', '_')}"
            
            # Get actual count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            actual_count = await conn.fetchval(count_query)
            
            print(f"  - {table_name}: {actual_count} مورد")
        
    finally:
        await conn.close()

async def separate_points_data():
    """Separate my_points data if needed"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="postgres",
        password="postgres",
        database="gis_backend"
    )
    
    try:
        print("\n🔧 بررسی داده‌های my_points")
        print("=" * 30)
        
        # Check if my_points needs separation
        check_query = """
            SELECT bcnshp, COUNT(*) as count
            FROM my_points 
            WHERE bcnshp IS NOT NULL
            GROUP BY bcnshp
        """
        
        bcnshp_rows = await conn.fetch(check_query)
        
        if len(bcnshp_rows) > 1:
            print(f"📊 {len(bcnshp_rows)} نوع فانوس مختلف یافت شد:")
            for row in bcnshp_rows:
                print(f"  - نوع {row['bcnshp']}: {row['count']} مورد")
            
            # Create separate tables
            for row in bcnshp_rows:
                bcnshp = row['bcnshp']
                count = row['count']
                
                table_name = f"beacon_type_{int(bcnshp)}"
                
                print(f"🔄 ایجاد جدول {table_name} ({count} مورد)...")
                
                create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} AS
                    SELECT * FROM my_points 
                    WHERE bcnshp = $1
                """
                
                await conn.execute(create_table_query, bcnshp)
                
                # Add spatial index
                add_index_query = f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_geom 
                    ON {table_name} USING GIST (geom)
                """
                
                await conn.execute(add_index_query)
                
                print(f"  ✅ جدول {table_name} ایجاد شد")
        else:
            print("❌ داده‌های my_points نیازی به تقسیم ندارند")
            print(f"  همه {bcnshp_rows[0]['count']} مورد از نوع {bcnshp_rows[0]['bcnshp']} هستند")
        
    finally:
        await conn.close()

async def main():
    """Main function"""
    print("🗺️ تقسیم‌بندی داده‌های جغرافیایی")
    print("=" * 40)
    
    # Separate turkaman_map data
    await separate_turkaman_data()
    
    # Separate my_points data
    await separate_points_data()
    
    print("\n✅ تمام عملیات تکمیل شد!")

if __name__ == "__main__":
    asyncio.run(main())
