import os
import json
from typing import Dict, Any, Optional, Tuple
import geopandas as gpd
from shapely.geometry import box
from shapely import wkt
import fiona
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import ShapefileLayer
from app.schemas.gis import ShapefileLayerCreate, Bounds
import logging

logger = logging.getLogger(__name__)


class ShapefileProcessor:
    """کلاس برای پردازش فایل‌های shapefile"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def process_shapefile(self, file_path: str, layer_name: str, description: str = None) -> ShapefileLayer:
        """
        پردازش فایل shapefile و ذخیره اطلاعات در دیتابیس
        """
        try:
            # بررسی وجود فایل
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"فایل shapefile یافت نشد: {file_path}")
            
            # خواندن فایل shapefile
            gdf = gpd.read_file(file_path)
            
            # استخراج اطلاعات
            file_size = os.path.getsize(file_path)
            crs = str(gdf.crs) if gdf.crs else "EPSG:4326"
            geometry_type = self._get_geometry_type(gdf)
            feature_count = len(gdf)
            bounds = self._calculate_bounds(gdf)
            attributes_schema = self._extract_attributes_schema(gdf)
            
            # ایجاد رکورد در دیتابیس
            layer_data = ShapefileLayerCreate(
                name=layer_name,
                description=description,
                file_path=file_path,
                file_size=file_size,
                crs=crs,
                geometry_type=geometry_type,
                feature_count=feature_count,
                bounds=bounds,
                attributes_schema=attributes_schema
            )
            
            # ذخیره در دیتابیس
            db_layer = ShapefileLayer(**layer_data.dict())
            self.db_session.add(db_layer)
            await self.db_session.commit()
            await self.db_session.refresh(db_layer)
            
            logger.info(f"لایه shapefile با موفقیت پردازش شد: {layer_name}")
            return db_layer
            
        except Exception as e:
            logger.error(f"خطا در پردازش shapefile: {str(e)}")
            raise
    
    def _get_geometry_type(self, gdf: gpd.GeoDataFrame) -> str:
        """تعیین نوع هندسه غالب در GeoDataFrame"""
        if gdf.empty:
            return "UNKNOWN"
        
        geometry_types = gdf.geometry.geom_type.unique()
        if len(geometry_types) == 1:
            return geometry_types[0].upper()
        else:
            return "MIXED"
    
    def _calculate_bounds(self, gdf: gpd.GeoDataFrame) -> Bounds:
        """محاسبه محدوده جغرافیایی"""
        if gdf.empty:
            return Bounds(minx=0, miny=0, maxx=0, maxy=0)
        
        bounds = gdf.total_bounds
        return Bounds(
            minx=float(bounds[0]),
            miny=float(bounds[1]),
            maxx=float(bounds[2]),
            maxy=float(bounds[3])
        )
    
    def _extract_attributes_schema(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """استخراج اسکیمای ویژگی‌ها"""
        schema = {}
        for column in gdf.columns:
            if column != 'geometry':
                dtype = str(gdf[column].dtype)
                schema[column] = {
                    "type": dtype,
                    "nullable": gdf[column].isnull().any()
                }
        return schema
    
    def get_layer_data(self, layer_id: int) -> Optional[gpd.GeoDataFrame]:
        """دریافت داده‌های لایه بر اساس شناسه"""
        # این متد باید در سرویس اصلی پیاده‌سازی شود
        pass
    
    def validate_shapefile(self, file_path: str) -> Tuple[bool, str]:
        """
        اعتبارسنجی فایل shapefile
        """
        try:
            # بررسی وجود فایل‌های مورد نیاز
            required_files = ['.shp', '.shx', '.dbf']
            base_name = os.path.splitext(file_path)[0]
            
            for ext in required_files:
                if not os.path.exists(f"{base_name}{ext}"):
                    return False, f"فایل مورد نیاز یافت نشد: {base_name}{ext}"
            
            # تلاش برای خواندن فایل
            with fiona.open(file_path) as src:
                if len(src) == 0:
                    return False, "فایل shapefile خالی است"
                
                # بررسی CRS
                if not src.crs:
                    return False, "سیستم مختصات تعریف نشده است"
            
            return True, "فایل معتبر است"
            
        except Exception as e:
            return False, f"خطا در اعتبارسنجی: {str(e)}"
    
    def get_shapefile_info(self, file_path: str) -> Dict[str, Any]:
        """
        دریافت اطلاعات کلی فایل shapefile
        """
        try:
            with fiona.open(file_path) as src:
                return {
                    "feature_count": len(src),
                    "crs": str(src.crs) if src.crs else None,
                    "schema": src.schema,
                    "bounds": src.bounds,
                    "driver": src.driver
                }
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات shapefile: {str(e)}")
            raise
