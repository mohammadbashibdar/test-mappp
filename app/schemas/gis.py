from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class Bounds(BaseModel):
    """مدل برای محدوده جغرافیایی"""
    minx: float
    miny: float
    maxx: float
    maxy: float


class Center(BaseModel):
    """مدل برای مرکز نقشه"""
    lat: float
    lng: float


class ShapefileLayerBase(BaseModel):
    """اساس مدل لایه shapefile"""
    name: str = Field(..., description="نام لایه")
    description: Optional[str] = Field(None, description="توضیحات لایه")
    crs: str = Field("EPSG:4326", description="سیستم مختصات")
    geometry_type: Optional[str] = Field(None, description="نوع هندسه")
    feature_count: Optional[int] = Field(0, description="تعداد ویژگی‌ها")
    bounds: Optional[Bounds] = Field(None, description="محدوده جغرافیایی")
    attributes_schema: Optional[Dict[str, Any]] = Field(None, description="اسکیمای ویژگی‌ها")


class ShapefileLayerCreate(ShapefileLayerBase):
    """مدل برای ایجاد لایه shapefile"""
    file_path: str = Field(..., description="مسیر فایل shapefile")
    file_size: Optional[int] = Field(None, description="حجم فایل")


class ShapefileLayerResponse(ShapefileLayerBase):
    """مدل پاسخ برای لایه shapefile"""
    id: int
    file_path: str
    file_size: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LayerStyleBase(BaseModel):
    """اساس مدل استایل لایه"""
    name: str = Field(..., description="نام استایل")
    style_config: Dict[str, Any] = Field(..., description="پیکربندی استایل")
    is_default: bool = Field(False, description="آیا استایل پیش‌فرض است")


class LayerStyleCreate(LayerStyleBase):
    """مدل برای ایجاد استایل لایه"""
    layer_id: int = Field(..., description="شناسه لایه")


class LayerStyleResponse(LayerStyleBase):
    """مدل پاسخ برای استایل لایه"""
    id: int
    layer_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TMSLayerBase(BaseModel):
    """اساس مدل لایه TMS"""
    name: str = Field(..., description="نام لایه TMS")
    title: Optional[str] = Field(None, description="عنوان لایه")
    description: Optional[str] = Field(None, description="توضیحات لایه")
    source_layer_id: Optional[int] = Field(None, description="شناسه لایه منبع")
    table_name: Optional[str] = Field(None, description="نام جدول در دیتابیس")
    filter_condition: Optional[str] = Field(None, description="شرط فیلتر برای لایه مجازی")
    min_zoom: int = Field(0, description="حداقل سطح زوم")
    max_zoom: int = Field(18, description="حداکثر سطح زوم")
    bounds: Optional[Bounds] = Field(None, description="محدوده جغرافیایی")
    center: Optional[Center] = Field(None, description="مرکز نقشه")
    crs: str = Field("EPSG:3857", description="سیستم مختصات")


class TMSLayerCreate(TMSLayerBase):
    """مدل برای ایجاد لایه TMS"""
    pass


class TMSLayerResponse(TMSLayerBase):
    """مدل پاسخ برای لایه TMS"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TileRequest(BaseModel):
    """مدل درخواست تایل"""
    layer_id: int = Field(..., description="شناسه لایه")
    z: int = Field(..., ge=0, le=22, description="سطح زوم")
    x: int = Field(..., ge=0, description="مختصات X تایل")
    y: int = Field(..., ge=0, description="مختصات Y تایل")
    format: str = Field("png", description="فرمت تایل")


class TMSInfo(BaseModel):
    """اطلاعات TMS"""
    title: str
    description: str
    version: str = "1.0.0"
    tms: str
    attribution: str
    crs: str = "EPSG:3857"
    bounds: Bounds
    center: Center
    min_zoom: int = 0
    max_zoom: int = 18
    layers: List[TMSLayerResponse]


class CapabilitiesResponse(BaseModel):
    """پاسخ قابلیت‌های TMS"""
    tms_info: TMSInfo
    layers: List[TMSLayerResponse]
