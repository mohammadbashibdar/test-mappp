import asyncio
from typing import List, Dict, Any, Optional, Tuple
import geopandas as gpd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseReader:
    """کلاس برای خواندن داده‌های جغرافیایی از دیتابیس PostgreSQL"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_available_tables(self) -> List[Dict[str, Any]]:
        """دریافت لیست جداول جغرافیایی موجود در دیتابیس"""
        try:
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    tableowner
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            
            result = await self.db_session.execute(query)
            tables = result.fetchall()
            
            # بررسی جداول جغرافیایی
            geo_tables = []
            for table in tables:
                table_name = table.tablename
                if await self._is_geographic_table(table_name):
                    geo_tables.append({
                        "name": table_name,
                        "schema": table.schemaname,
                        "owner": table.tableowner,
                        "type": "geographic"
                    })
            
            return geo_tables
            
        except Exception as e:
            logger.error(f"خطا در دریافت جداول: {str(e)}")
            return []
    
    async def _is_geographic_table(self, table_name: str) -> bool:
        """بررسی اینکه آیا جدول شامل داده‌های جغرافیایی است"""
        try:
            # بررسی وجود ستون geometry با نام‌های مختلف
            query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND (
                    data_type LIKE '%geometry%' 
                    OR data_type = 'USER-DEFINED' 
                    OR column_name LIKE '%geom%'
                    OR column_name = 'geometry'
                    OR column_name = 'the_geom'
                )
            """)
            
            result = await self.db_session.execute(query, {"table_name": table_name})
            columns = result.fetchall()
            
            # اگر ستون geometry پیدا شد، بررسی کن که آیا واقعاً داده جغرافیایی دارد
            if len(columns) > 0:
                # بررسی وجود داده در ستون geometry
                geom_column = columns[0].column_name
                count_query = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE {geom_column} IS NOT NULL
                """)
                
                count_result = await self.db_session.execute(count_query)
                count = count_result.scalar()
                
                return count > 0
            
            return False
            
        except Exception as e:
            logger.error(f"خطا در بررسی جدول {table_name}: {str(e)}")
            return False
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """دریافت اطلاعات تفصیلی یک جدول"""
        try:
            # اطلاعات کلی جدول
            query = text(f"""
                SELECT 
                    COUNT(*) as feature_count,
                    ST_Extent(geom) as bounds,
                    (SELECT ST_SRID(geom) FROM {table_name} WHERE geom IS NOT NULL LIMIT 1) as srid
                FROM {table_name}
                WHERE geom IS NOT NULL
            """)
            
            result = await self.db_session.execute(query)
            info = result.fetchone()
            
            # اطلاعات ستون‌ها
            columns_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """)
            
            columns_result = await self.db_session.execute(columns_query, {"table_name": table_name})
            columns = columns_result.fetchall()
            
            # تعیین نوع هندسه
            geom_type_query = text(f"""
                SELECT ST_GeometryType(geom) as geom_type
                FROM {table_name}
                WHERE geom IS NOT NULL
                LIMIT 1
            """)
            
            geom_result = await self.db_session.execute(geom_type_query)
            geom_type = geom_result.fetchone()
            
            # تبدیل bounds از BOX format به dict
            bounds_dict = None
            if info and info.bounds:
                bounds_str = str(info.bounds)
                # استخراج مختصات از BOX(48.0 24.0,60.0 31.0)
                coords = bounds_str.replace('BOX(', '').replace(')', '').split(',')
                min_coords = coords[0].split()
                max_coords = coords[1].split()
                
                bounds_dict = {
                    "minx": float(min_coords[0]),
                    "miny": float(min_coords[1]),
                    "maxx": float(max_coords[0]),
                    "maxy": float(max_coords[1])
                }
            
            return {
                "name": table_name,
                "feature_count": info.feature_count if info else 0,
                "bounds": bounds_dict,
                "srid": info.srid if info else None,
                "geometry_type": geom_type.geom_type if geom_type else None,
                "columns": [
                    {
                        "name": col.column_name,
                        "type": col.data_type,
                        "nullable": col.is_nullable == "YES"
                    }
                    for col in columns
                ]
            }
            
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات جدول {table_name}: {str(e)}")
            return {}
    
    async def get_features_in_bounds(
        self, 
        table_name: str, 
        bounds: Tuple[float, float, float, float],
        srid: int = 4326
    ) -> List[Dict[str, Any]]:
        """دریافت ویژگی‌های موجود در محدوده مشخص"""
        try:
            minx, miny, maxx, maxy = bounds
            
            query = text(f"""
                SELECT 
                    ST_AsGeoJSON(geom) as geometry,
                    *
                FROM {table_name}
                WHERE ST_Intersects(
                    geom, 
                    ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, :srid)
                )
                LIMIT 1000
            """)
            
            result = await self.db_session.execute(query, {
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "srid": srid
            })
            
            features = []
            for row in result.fetchall():
                feature = dict(row._mapping)
                features.append(feature)
            
            return features
            
        except Exception as e:
            logger.error(f"خطا در دریافت ویژگی‌ها: {str(e)}")
            return []
    
    async def get_table_bounds(self, table_name: str) -> Optional[Tuple[float, float, float, float]]:
        """دریافت محدوده جغرافیایی جدول"""
        try:
            query = text(f"""
                SELECT ST_Extent(geom) as bounds
                FROM {table_name}
                WHERE geom IS NOT NULL
            """)
            
            result = await self.db_session.execute(query)
            bounds_result = result.fetchone()
            
            if bounds_result and bounds_result.bounds:
                # تبدیل از BOX format به tuple
                bounds_str = str(bounds_result.bounds)
                # استخراج مختصات از BOX(48.0 24.0,60.0 31.0)
                coords = bounds_str.replace('BOX(', '').replace(')', '').split(',')
                min_coords = coords[0].split()
                max_coords = coords[1].split()
                
                return (
                    float(min_coords[0]),  # minx
                    float(min_coords[1]),  # miny
                    float(max_coords[0]),  # maxx
                    float(max_coords[1])   # maxy
                )
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در دریافت محدوده جدول {table_name}: {str(e)}")
            return None
    
    async def get_layer_data_for_tile(
        self, 
        table_name: str, 
        tile_bounds: Tuple[float, float, float, float],
        zoom_level: int
    ) -> List[Dict[str, Any]]:
        """دریافت داده‌های لایه برای تولید تایل"""
        try:
            # تنظیم تعداد ویژگی‌ها بر اساس سطح زوم
            limit = min(1000, max(100, 2000 // (zoom_level + 1)))
            
            minx, miny, maxx, maxy = tile_bounds
            
            query = text(f"""
                SELECT 
                    ST_AsGeoJSON(geom) as geometry,
                    *
                FROM {table_name}
                WHERE ST_Intersects(
                    geom, 
                    ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
                )
                LIMIT :limit
            """)
            
            result = await self.db_session.execute(query, {
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "limit": limit
            })
            
            features = []
            for row in result.fetchall():
                feature = dict(row._mapping)
                features.append(feature)
            
            return features
            
        except Exception as e:
            logger.error(f"خطا در دریافت داده‌های تایل: {str(e)}")
            return []
