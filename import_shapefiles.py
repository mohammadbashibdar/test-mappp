#!/usr/bin/env python3
"""
اسکریپت import فایل‌های shapefile به دیتابیس PostgreSQL
"""

import geopandas as gpd
import asyncio
import asyncpg
import os
from pathlib import Path

async def import_shapefile(shp_path: str, table_name: str):
    """import یک فایل shapefile به دیتابیس"""
    try:
        print(f"📁 خواندن فایل: {shp_path}")
        
        # خواندن فایل shapefile
        gdf = gpd.read_file(shp_path)
        print(f"✅ {len(gdf)} ویژگی خوانده شد")
        print(f"   ستون‌ها: {list(gdf.columns)}")
        print(f"   نوع هندسه: {gdf.geometry.geom_type.unique()}")
        
        # اتصال به دیتابیس
        conn = await asyncpg.connect('postgresql://postgres:postgres@db:5432/gis_backend')
        
        # حذف جدول قبلی اگر وجود دارد
        await conn.execute(f'DROP TABLE IF EXISTS {table_name};')
        
        # ایجاد جدول جدید
        columns = []
        for col in gdf.columns:
            if col != 'geometry':
                col_type = 'TEXT'
                if gdf[col].dtype == 'int64':
                    col_type = 'INTEGER'
                elif gdf[col].dtype == 'float64':
                    col_type = 'REAL'
                columns.append(f'"{col}" {col_type}')
        
        create_table_sql = f'''
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                {', '.join(columns)},
                geom GEOMETRY({gdf.geometry.geom_type.unique()[0]}, 4326)
            );
        '''
        
        await conn.execute(create_table_sql)
        print(f"✅ جدول {table_name} ایجاد شد")
        
        # insert داده‌ها
        for idx, row in gdf.iterrows():
            geom_wkt = row.geometry.wkt
            
            # ساخت query
            cols = [f'"{col}"' for col in gdf.columns if col != 'geometry']
            placeholders = [f'${i+1}' for i in range(len(cols))]
            values = [row[col] for col in gdf.columns if col != 'geometry']
            
            insert_sql = f'''
                INSERT INTO {table_name} ({', '.join(cols)}, geom)
                VALUES ({', '.join(placeholders)}, ST_GeomFromText(${len(values)+1}, 4326))
            '''
            
            await conn.execute(insert_sql, *values, geom_wkt)
        
        await conn.close()
        print(f"✅ {table_name} با موفقیت import شد")
        return True
        
    except Exception as e:
        print(f"❌ خطا در import {table_name}: {e}")
        return False

async def main():
    """تابع اصلی"""
    # مسیر فایل‌ها (داخل container)
    data_dir = Path("/app/data")
    
    # لیست فایل‌های shapefile
    shapefiles = [
        ("6_WRECKS_Point.shp", "wrecks_point"),
        ("6_UWTROC_Point.shp", "uwtroc_point"), 
        ("6_LIGHTS_Point.shp", "lights_point"),
        ("6_LNDELV_Point.shp", "lndelv_point"),
        ("6_LNDMRK_Point.shp", "lndmrk_point"),
        ("6_BCNSPP_Point.shp", "bcnsp_point"),
        ("6_ROADWY_Arc.shp", "roadwy_arc"),
        ("6_PIPSOL_Arc.shp", "pipsol_arc"),
        ("6_DEPCNT_Arc.shp", "depcnt_arc"),
        ("6_LNDARE_Polygon.shp", "lndare_polygon"),
        ("6_BUAARE_Polygon.shp", "buaare_polygon"),
    ]
    
    success_count = 0
    total_count = len(shapefiles)
    
    for shp_file, table_name in shapefiles:
        shp_path = data_dir / shp_file
        if shp_path.exists():
            if await import_shapefile(str(shp_path), table_name):
                success_count += 1
            print("-" * 50)
        else:
            print(f"⚠️ فایل یافت نشد: {shp_path}")
    
    print(f"\n🎉 کار تمام شد: {success_count}/{total_count} فایل با موفقیت import شدند")

if __name__ == "__main__":
    asyncio.run(main())
