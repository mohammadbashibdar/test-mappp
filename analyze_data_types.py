#!/usr/bin/env python3
"""
Analyze data types in the my_points table to see if they need to be separated
"""

import asyncio
import asyncpg
import json
from collections import Counter

async def analyze_data_types():
    """Analyze the data types in my_points table"""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="postgres",
        password="postgres",
        database="gis_db"
    )
    
    try:
        # Get all data from my_points table
        rows = await conn.fetch("""
            SELECT gid, bcnshp, catspm, colour, colpat, objnam, nobjnm, 
                   txtdsc, ntxtds, inform, ninfom, status, condtn
            FROM my_points 
            ORDER BY gid
        """)
        
        print("🔍 تحلیل انواع داده‌ها در جدول my_points")
        print("=" * 60)
        print(f"تعداد کل رکوردها: {len(rows)}")
        print()
        
        # Analyze bcnshp (beacon shape) values
        bcnshp_values = [row['bcnshp'] for row in rows if row['bcnshp'] is not None]
        bcnshp_counter = Counter(bcnshp_values)
        
        print("📊 انواع فانوس دریایی (bcnshp):")
        for value, count in bcnshp_counter.most_common():
            print(f"  - نوع {value}: {count} مورد")
        print()
        
        # Analyze catspm (category) values
        catspm_values = [row['catspm'] for row in rows if row['catspm'] is not None]
        catspm_counter = Counter(catspm_values)
        
        if catspm_counter:
            print("📊 دسته‌بندی (catspm):")
            for value, count in catspm_counter.most_common():
                print(f"  - {value}: {count} مورد")
            print()
        
        # Analyze objnam (object name) values
        objnam_values = [row['objnam'] for row in rows if row['objnam'] is not None]
        objnam_counter = Counter(objnam_values)
        
        if objnam_counter:
            print("📊 نام اشیاء (objnam):")
            for value, count in objnam_counter.most_common():
                print(f"  - {value}: {count} مورد")
            print()
        
        # Analyze txtdsc (text description) values
        txtdsc_values = [row['txtdsc'] for row in rows if row['txtdsc'] is not None]
        txtdsc_counter = Counter(txtdsc_values)
        
        if txtdsc_counter:
            print("📊 توضیحات متنی (txtdsc):")
            for value, count in txtdsc_counter.most_common():
                print(f"  - {value}: {count} مورد")
            print()
        
        # Show sample records for each bcnshp type
        print("🔍 نمونه رکوردها برای هر نوع:")
        for bcnshp_type in sorted(bcnshp_counter.keys()):
            print(f"\n--- نوع فانوس {bcnshp_type} ---")
            sample_rows = [row for row in rows if row['bcnshp'] == bcnshp_type][:3]
            
            for row in sample_rows:
                print(f"  GID {row['gid']}:")
                print(f"    - bcnshp: {row['bcnshp']}")
                print(f"    - catspm: {row['catspm']}")
                print(f"    - objnam: {row['objnam']}")
                print(f"    - txtdsc: {row['txtdsc']}")
                print(f"    - status: {row['status']}")
                print()
        
        # Check if data should be separated
        print("🤔 آیا داده‌ها باید تقسیم شوند؟")
        print("=" * 40)
        
        if len(bcnshp_counter) > 1:
            print("✅ بله! داده‌ها بر اساس bcnshp (نوع فانوس) قابل تقسیم هستند:")
            for value, count in bcnshp_counter.items():
                print(f"  - نوع {value}: {count} مورد")
        else:
            print("❌ خیر، همه داده‌ها از یک نوع هستند")
        
        if len(catspm_counter) > 1:
            print("✅ داده‌ها بر اساس catspm (دسته‌بندی) نیز قابل تقسیم هستند:")
            for value, count in catspm_counter.items():
                print(f"  - {value}: {count} مورد")
        
        # Suggest separation strategy
        print("\n💡 پیشنهاد تقسیم‌بندی:")
        print("=" * 30)
        
        if len(bcnshp_counter) > 1:
            print("1. تقسیم بر اساس bcnshp (نوع فانوس):")
            for value, count in bcnshp_counter.items():
                table_name = f"beacon_type_{int(value)}" if value else "beacon_unknown"
                print(f"   - جدول: {table_name} ({count} مورد)")
        
        if len(catspm_counter) > 1:
            print("2. تقسیم بر اساس catspm (دسته‌بندی):")
            for value, count in catspm_counter.items():
                table_name = f"category_{value.lower().replace(' ', '_')}" if value else "category_unknown"
                print(f"   - جدول: {table_name} ({count} مورد)")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_data_types())
