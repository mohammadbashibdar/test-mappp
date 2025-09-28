#!/usr/bin/env python3
"""
تست ساده برای اتصال به دیتابیس و دریافت جداول
"""
import asyncio
import sys
import os
sys.path.append('/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test_database():
    """تست اتصال به دیتابیس"""
    try:
        # ایجاد اتصال
        DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/gis_backend"
        engine = create_async_engine(DATABASE_URL)
        
        async with engine.begin() as conn:
            # تست ساده
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()
            print(f"تست اتصال: {test_value}")
            
            # دریافت جداول
            result = await conn.execute(text("""
                SELECT schemaname, tablename, tableowner
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
                LIMIT 10
            """))
            tables = result.fetchall()
            print(f"تعداد جداول: {len(tables)}")
            
            for table in tables:
                print(f"جدول: {table.tablename}")
                
                # بررسی ستون geometry
                geom_result = await conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    AND (data_type LIKE '%geometry%' OR data_type = 'USER-DEFINED' 
                         OR column_name LIKE '%geom%' OR column_name = 'wkb_geometry')
                    LIMIT 1
                """), {"table_name": table.tablename})
                
                geom_row = geom_result.fetchone()
                if geom_row:
                    print(f"  -> جغرافیایی: {geom_row.column_name}")
                else:
                    print(f"  -> غیر جغرافیایی")
        
        await engine.dispose()
        print("تست موفق!")
        
    except Exception as e:
        print(f"خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database())
