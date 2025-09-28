import io
import math
import json
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw
import mercantile
from shapely.geometry import box, Point, LineString, Polygon
from shapely.ops import transform
from shapely import wkt
import pyproj
from functools import partial
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.gis import TMSLayer, TileCache
from app.schemas.gis import TMSLayerCreate, Bounds, Center
from app.services.database_reader import DatabaseReader
import logging

logger = logging.getLogger(__name__)


class TMSService:
    """سرویس TMS برای تولید تایل‌های نقشه از دیتابیس"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.db_reader = DatabaseReader(db_session)
        self.tile_size = 256
        self.default_style = {
            "point": {"color": "#FF0000", "size": 4, "stroke_color": "#FFFFFF", "stroke_width": 1},
            "line": {"color": "#0000FF", "width": 2},
            "polygon": {"fill_color": "#00FF00", "stroke_color": "#000000", "stroke_width": 1}
        }
    
    async def create_tms_layer_from_database(self, table_name: str, layer_name: str, title: str = None) -> TMSLayer:
        """ایجاد لایه TMS از جدول دیتابیس"""
        try:
            # دریافت اطلاعات جدول
            table_info = await self.db_reader.get_table_info(table_name)
            if not table_info:
                raise ValueError(f"جدول {table_name} یافت نشد یا داده‌های جغرافیایی ندارد")
            
            # محاسبه محدوده
            bounds = await self.db_reader.get_table_bounds(table_name)
            if bounds:
                bounds_dict = {
                    "minx": bounds[0],
                    "miny": bounds[1], 
                    "maxx": bounds[2],
                    "maxy": bounds[3]
                }
                center = self._calculate_center(bounds_dict)
            else:
                bounds_dict = None
                center = None
            
            # ایجاد لایه TMS
            tms_layer = TMSLayer(
                name=layer_name,
                title=title or layer_name,
                description=f"لایه {table_name} از دیتابیس",
                source_layer_id=None,  # مستقیماً از دیتابیس می‌خوانیم
                table_name=table_name,  # نام جدول در دیتابیس
                bounds=bounds_dict,
                center=center.dict() if center else None,
                crs="EPSG:4326",
                is_active=True
            )
            
            self.db_session.add(tms_layer)
            await self.db_session.commit()
            await self.db_session.refresh(tms_layer)
            
            logger.info(f"لایه TMS از دیتابیس ایجاد شد: {layer_name} -> {table_name}")
            return tms_layer
            
        except Exception as e:
            logger.error(f"خطا در ایجاد لایه TMS از دیتابیس: {str(e)}")
            raise
    
    async def get_tile(self, layer_id: int, z: int, x: int, y: int, format: str = "png") -> Optional[bytes]:
        """دریافت تایل نقشه"""
        try:
            # بررسی کش
            cached_tile = await self._get_cached_tile(layer_id, z, x, y, format)
            if cached_tile:
                return cached_tile
            
            # تولید تایل جدید
            tile_data = await self._generate_tile(layer_id, z, x, y, format)
            
            # ذخیره در کش
            if tile_data:
                await self._cache_tile(layer_id, z, x, y, tile_data, format)
            
            return tile_data
            
        except Exception as e:
            logger.error(f"خطا در تولید تایل: {str(e)}")
            return None
    
    async def _get_cached_tile(self, layer_id: int, z: int, x: int, y: int, format: str) -> Optional[bytes]:
        """دریافت تایل از کش"""
        try:
            result = await self.db_session.execute(
                select(TileCache).where(
                    TileCache.layer_id == layer_id,
                    TileCache.z == z,
                    TileCache.x == x,
                    TileCache.y == y,
                    TileCache.format == format
                )
            )
            cached_tile = result.scalar_one_or_none()
            return cached_tile.tile_data if cached_tile else None
        except Exception as e:
            logger.error(f"خطا در دریافت تایل از کش: {str(e)}")
            return None
    
    async def _cache_tile(self, layer_id: int, z: int, x: int, y: int, tile_data: bytes, format: str):
        """ذخیره تایل در کش"""
        try:
            tile_cache = TileCache(
                layer_id=layer_id,
                z=z,
                x=x,
                y=y,
                tile_data=tile_data,
                format=format,
                size=len(tile_data)
            )
            self.db_session.add(tile_cache)
            await self.db_session.commit()
        except Exception as e:
            logger.error(f"خطا در ذخیره تایل در کش: {str(e)}")
    
    async def _generate_tile(self, layer_id: int, z: int, x: int, y: int, format: str) -> Optional[bytes]:
        """تولید تایل نقشه از دیتابیس"""
        try:
            # دریافت اطلاعات لایه
            tms_layer = await self._get_tms_layer(layer_id)
            if not tms_layer:
                return None
            
            # محاسبه محدوده تایل
            tile_bounds = self._tile_to_bounds(x, y, z)
            
            # دریافت داده‌ها از دیتابیس
            if hasattr(tms_layer, 'table_name') and tms_layer.table_name:
                # استفاده از فیلتر اگر موجود باشد
                filter_condition = getattr(tms_layer, 'filter_condition', None)
                features = await self.db_reader.get_layer_data_for_tile(
                    tms_layer.table_name, 
                    tile_bounds, 
                    z,
                    filter_condition
                )
            else:
                return self._create_empty_tile(format)
            
            if not features:
                return self._create_empty_tile(format)
            
            # تولید تصویر تایل
            tile_image = self._render_tile_from_features(features, tile_bounds, z)
            
            # تبدیل به فرمت مورد نظر
            return self._image_to_bytes(tile_image, format)
            
        except Exception as e:
            logger.error(f"خطا در تولید تایل: {str(e)}")
            return None
    
    def _tile_to_bounds(self, x: int, y: int, z: int) -> Tuple[float, float, float, float]:
        """تبدیل مختصات تایل به محدوده جغرافیایی"""
        # تبدیل به Web Mercator
        west, south = mercantile.xy(mercantile.ul(x, y, z))
        east, north = mercantile.xy(mercantile.ul(x + 1, y + 1, z))
        
        # تبدیل به WGS84
        transformer = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        west, south = transformer.transform(west, south)
        east, north = transformer.transform(east, north)
        
        return west, south, east, north
    
    def _filter_data_by_bounds(self, gdf, bounds: Tuple[float, float, float, float]):
        """فیلتر کردن داده‌ها بر اساس محدوده تایل"""
        west, south, east, north = bounds
        tile_bbox = box(west, south, east, north)
        
        # فیلتر کردن بر اساس تقاطع
        mask = gdf.geometry.intersects(tile_bbox)
        return gdf[mask].copy()
    
    def _render_tile_from_features(self, features: List[Dict[str, Any]], bounds: Tuple[float, float, float, float], z: int) -> Image.Image:
        """رندر کردن تایل از ویژگی‌های دیتابیس"""
        west, south, east, north = bounds
        
        # ایجاد تصویر
        img = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # محاسبه مقیاس
        scale_x = self.tile_size / (east - west)
        scale_y = self.tile_size / (north - south)
        
        # رندر کردن هر ویژگی
        for feature in features:
            try:
                # پارس کردن geometry از GeoJSON
                if 'geometry' in feature and feature['geometry']:
                    geom_data = json.loads(feature['geometry'])
                    geometry = self._parse_geojson_geometry(geom_data)
                    
                    if geometry and not geometry.is_empty:
                        # تبدیل مختصات به پیکسل
                        pixel_coords = self._geometry_to_pixels(geometry, west, south, scale_x, scale_y)
                        
                        # رسم بر اساس نوع هندسه
                        if geometry.geom_type == 'Point':
                            self._draw_point(draw, pixel_coords, z)
                        elif geometry.geom_type in ['LineString', 'MultiLineString']:
                            self._draw_line(draw, pixel_coords, z)
                        elif geometry.geom_type in ['Polygon', 'MultiPolygon']:
                            self._draw_polygon(draw, pixel_coords, z)
            except Exception as e:
                logger.warning(f"خطا در رندر ویژگی: {str(e)}")
                continue
        
        return img
    
    def _parse_geojson_geometry(self, geom_data: Dict[str, Any]):
        """پارس کردن geometry از GeoJSON"""
        try:
            from shapely.geometry import shape
            return shape(geom_data)
        except Exception as e:
            logger.warning(f"خطا در پارس geometry: {str(e)}")
            return None
    
    def _geometry_to_pixels(self, geometry, west: float, south: float, scale_x: float, scale_y: float):
        """تبدیل هندسه به مختصات پیکسل"""
        def transform_coords(coords):
            x = int((coords[0] - west) * scale_x)
            y = int((north - coords[1]) * scale_y)  # معکوس کردن Y
            return (x, y)
        
        if geometry.geom_type == 'Point':
            return transform_coords(geometry.coords[0])
        elif geometry.geom_type == 'LineString':
            return [transform_coords(coord) for coord in geometry.coords]
        elif geometry.geom_type == 'Polygon':
            return [[transform_coords(coord) for coord in ring.coords] for ring in geometry.geoms]
        elif geometry.geom_type == 'MultiPoint':
            return [transform_coords(point.coords[0]) for point in geometry.geoms]
        elif geometry.geom_type == 'MultiLineString':
            return [[transform_coords(coord) for coord in line.coords] for line in geometry.geoms]
        elif geometry.geom_type == 'MultiPolygon':
            return [[[transform_coords(coord) for coord in ring.coords] for ring in poly.geoms] for poly in geometry.geoms]
        
        return []
    
    def _draw_point(self, draw: ImageDraw.Draw, coords: Tuple[int, int], z: int):
        """رسم نقطه"""
        if not coords:
            return
        
        x, y = coords
        size = max(2, min(8, 12 - z))  # اندازه بر اساس سطح زوم
        
        # دایره
        draw.ellipse([x-size, y-size, x+size, y+size], 
                    fill=self.default_style["point"]["color"],
                    outline=self.default_style["point"]["stroke_color"],
                    width=self.default_style["point"]["stroke_width"])
    
    def _draw_line(self, draw: ImageDraw.Draw, coords: List[Tuple[int, int]], z: int):
        """رسم خط"""
        if len(coords) < 2:
            return
        
        width = max(1, min(4, 8 - z))  # عرض بر اساس سطح زوم
        
        for i in range(len(coords) - 1):
            draw.line([coords[i], coords[i+1]], 
                     fill=self.default_style["line"]["color"],
                     width=width)
    
    def _draw_polygon(self, draw: ImageDraw.Draw, coords: List[List[Tuple[int, int]]], z: int):
        """رسم چندضلعی"""
        if not coords:
            return
        
        width = max(1, min(3, 6 - z))  # عرض خط بر اساس سطح زوم
        
        for ring in coords:
            if len(ring) < 3:
                continue
            
            # پر کردن
            draw.polygon(ring, fill=self.default_style["polygon"]["fill_color"])
            
            # خط مرزی
            draw.polygon(ring, outline=self.default_style["polygon"]["stroke_color"], width=width)
    
    def _create_empty_tile(self, format: str) -> bytes:
        """ایجاد تایل خالی"""
        img = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
        return self._image_to_bytes(img, format)
    
    def _image_to_bytes(self, img: Image.Image, format: str) -> bytes:
        """تبدیل تصویر به بایت"""
        buffer = io.BytesIO()
        
        if format.lower() == 'png':
            img.save(buffer, format='PNG')
        elif format.lower() in ['jpg', 'jpeg']:
            # تبدیل به RGB برای JPEG
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            rgb_img.save(buffer, format='JPEG', quality=85)
        else:
            img.save(buffer, format='PNG')
        
        return buffer.getvalue()
    
    def _calculate_center(self, bounds: Dict[str, float]) -> Center:
        """محاسبه مرکز نقشه"""
        center_lng = (bounds['minx'] + bounds['maxx']) / 2
        center_lat = (bounds['miny'] + bounds['maxy']) / 2
        return Center(lat=center_lat, lng=center_lng)
    
    async def _get_tms_layer(self, layer_id: int) -> Optional[TMSLayer]:
        """دریافت لایه TMS"""
        result = await self.db_session.execute(
            select(TMSLayer).where(TMSLayer.id == layer_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_source_layer(self, layer_id: int):
        """دریافت لایه منبع"""
        result = await self.db_session.execute(
            select(ShapefileLayer).where(ShapefileLayer.id == layer_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_source_data(self, source_layer_id: int):
        """دریافت داده‌های لایه منبع"""
        source_layer = await self._get_source_layer(source_layer_id)
        if not source_layer:
            return None
        
        try:
            return gpd.read_file(source_layer.file_path)
        except Exception as e:
            logger.error(f"خطا در خواندن فایل shapefile: {str(e)}")
            return None
