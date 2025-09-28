#!/usr/bin/env python3
"""
Clean up unnecessary tables and keep only the original ones
"""

import asyncio
import asyncpg

async def cleanup_tables():
    """Remove unnecessary line_* tables"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="postgres",
        password="postgres",
        database="gis_backend"
    )
    
    try:
        print("🧹 شروع پاکسازی جدول‌های اضافی")
        print("=" * 40)
        
        # Get all line_* tables
        tables_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'line_%'
            ORDER BY tablename
        """
        
        tables = await conn.fetch(tables_query)
        
        print(f"📊 {len(tables)} جدول اضافی یافت شد:")
        for table in tables:
            print(f"  - {table['tablename']}")
        
        print("\n🗑️ حذف جدول‌های اضافی...")
        
        for table in tables:
            table_name = table['tablename']
            print(f"  حذف {table_name}...")
            
            # Drop table
            drop_query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
            await conn.execute(drop_query)
            print(f"    ✅ {table_name} حذف شد")
        
        print("\n✅ پاکسازی تکمیل شد!")
        
        # Show remaining tables
        remaining_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """
        
        remaining = await conn.fetch(remaining_query)
        
        print(f"\n📋 جدول‌های باقی‌مانده ({len(remaining)} جدول):")
        for table in remaining:
            print(f"  - {table['tablename']}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup_tables())
