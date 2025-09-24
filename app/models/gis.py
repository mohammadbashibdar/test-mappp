from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.models.base import Base


class ShapefileLayer(Base):
    """مدل برای ذخیره اطلاعات لایه‌های shapefile"""
    __tablename__ = "shapefile_layers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    crs = Column(String(50), default="EPSG:4326")
    geometry_type = Column(String(50))  # POINT, LINESTRING, POLYGON, etc.
    feature_count = Column(Integer, default=0)
    bounds = Column(JSONB)  # {"minx": x, "miny": y, "maxx": x, "maxy": y}
    attributes_schema = Column(JSONB)  # Schema of attribute fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TileCache(Base):
    """مدل برای کش کردن تایل‌های نقشه"""
    __tablename__ = "tile_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    layer_id = Column(Integer, nullable=False, index=True)
    z = Column(Integer, nullable=False)  # zoom level
    x = Column(Integer, nullable=False)  # tile x coordinate
    y = Column(Integer, nullable=False)  # tile y coordinate
    tile_data = Column(LargeBinary)  # PNG/JPEG tile data
    format = Column(String(10), default="png")  # png, jpeg
    size = Column(Integer)  # tile size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Composite unique index for efficient lookups
    __table_args__ = (
        {"extend_existing": True}
    )


class LayerStyle(Base):
    """مدل برای ذخیره استایل‌های لایه‌ها"""
    __tablename__ = "layer_styles"
    
    id = Column(Integer, primary_key=True, index=True)
    layer_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    style_config = Column(JSONB)  # Style configuration as JSON
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TMSLayer(Base):
    """مدل برای مدیریت لایه‌های TMS"""
    __tablename__ = "tms_layers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255))
    description = Column(Text)
    source_layer_id = Column(Integer)  # Reference to shapefile layer
    table_name = Column(String(255))  # نام جدول در دیتابیس PostgreSQL
    min_zoom = Column(Integer, default=0)
    max_zoom = Column(Integer, default=18)
    bounds = Column(JSONB)
    center = Column(JSONB)  # {"lat": y, "lng": x}
    crs = Column(String(50), default="EPSG:4326")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
