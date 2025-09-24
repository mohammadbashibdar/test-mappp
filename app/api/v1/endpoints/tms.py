from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import io

from app.core.database import get_db
from app.models.gis import TMSLayer, ShapefileLayer
from app.schemas.gis import (
    TMSLayerCreate, TMSLayerResponse, TMSInfo, CapabilitiesResponse,
    Bounds, Center
)
from app.services.tms_service import TMSService
from app.services.shapefile_processor import ShapefileProcessor

router = APIRouter(prefix="/tms", tags=["TMS"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(db: AsyncSession = Depends(get_db)):
    """دریافت قابلیت‌های TMS"""
    try:
        # دریافت تمام لایه‌های فعال
        result = await db.execute(
            select(TMSLayer).where(TMSLayer.is_active == True)
        )
        layers = result.scalars().all()
        
        # محاسبه محدوده کلی
        if layers:
            all_bounds = [layer.bounds for layer in layers if layer.bounds]
            if all_bounds:
                minx = min(b['minx'] for b in all_bounds)
                miny = min(b['miny'] for b in all_bounds)
                maxx = max(b['maxx'] for b in all_bounds)
                maxy = max(b['maxy'] for b in all_bounds)
                bounds = Bounds(minx=minx, miny=miny, maxx=maxx, maxy=maxy)
                center = Center(lat=(miny + maxy) / 2, lng=(minx + maxx) / 2)
            else:
                bounds = Bounds(minx=-180, miny=-90, maxx=180, maxy=90)
                center = Center(lat=0, lng=0)
        else:
            bounds = Bounds(minx=-180, miny=-90, maxx=180, maxy=90)
            center = Center(lat=0, lng=0)
        
        tms_info = TMSInfo(
            title="GIS Map Game TMS",
            description="Tile Map Service for GIS Map Game",
            version="1.0.0",
            tms="http://localhost:8000/api/v1/tms",
            attribution="GIS Map Game",
            crs="EPSG:3857",
            bounds=bounds,
            center=center,
            min_zoom=0,
            max_zoom=18,
            layers=[TMSLayerResponse.from_orm(layer) for layer in layers]
        )
        
        return CapabilitiesResponse(
            tms_info=tms_info,
            layers=[TMSLayerResponse.from_orm(layer) for layer in layers]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت قابلیت‌ها: {str(e)}")


@router.get("/{layer_id}/{z}/{x}/{y}.{format}")
async def get_tile(
    layer_id: int,
    z: int,
    x: int,
    y: int,
    format: str = "png",
    db: AsyncSession = Depends(get_db)
):
    """دریافت تایل نقشه"""
    try:
        # بررسی محدوده زوم
        if z < 0 or z > 22:
            raise HTTPException(status_code=400, detail="سطح زوم نامعتبر")
        
        # بررسی محدوده تایل
        max_tile = 2 ** z
        if x < 0 or x >= max_tile or y < 0 or y >= max_tile:
            raise HTTPException(status_code=400, detail="مختصات تایل نامعتبر")
        
        # بررسی فرمت
        if format.lower() not in ['png', 'jpg', 'jpeg']:
            raise HTTPException(status_code=400, detail="فرمت نامعتبر")
        
        # تولید تایل
        tms_service = TMSService(db)
        tile_data = await tms_service.get_tile(layer_id, z, x, y, format)
        
        if not tile_data:
            # تایل خالی
            from PIL import Image
            import io
            img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            tile_data = buffer.getvalue()
        
        # تعیین نوع محتوا
        content_type = "image/png" if format.lower() == "png" else "image/jpeg"
        
        return Response(
            content=tile_data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید تایل: {str(e)}")


@router.get("/layers", response_model=List[TMSLayerResponse])
async def get_layers(
    active_only: bool = Query(True, description="فقط لایه‌های فعال"),
    db: AsyncSession = Depends(get_db)
):
    """دریافت لیست لایه‌های TMS"""
    try:
        query = select(TMSLayer)
        if active_only:
            query = query.where(TMSLayer.is_active == True)
        
        result = await db.execute(query)
        layers = result.scalars().all()
        
        return [TMSLayerResponse.from_orm(layer) for layer in layers]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه‌ها: {str(e)}")


@router.post("/layers", response_model=TMSLayerResponse)
async def create_layer(
    layer_data: TMSLayerCreate,
    db: AsyncSession = Depends(get_db)
):
    """ایجاد لایه TMS جدید"""
    try:
        tms_service = TMSService(db)
        layer = await tms_service.create_tms_layer(layer_data)
        return TMSLayerResponse.from_orm(layer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد لایه: {str(e)}")


@router.get("/layers/{layer_id}", response_model=TMSLayerResponse)
async def get_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """دریافت اطلاعات لایه TMS"""
    try:
        result = await db.execute(
            select(TMSLayer).where(TMSLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        return TMSLayerResponse.from_orm(layer)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه: {str(e)}")


@router.put("/layers/{layer_id}", response_model=TMSLayerResponse)
async def update_layer(
    layer_id: int,
    layer_data: TMSLayerCreate,
    db: AsyncSession = Depends(get_db)
):
    """به‌روزرسانی لایه TMS"""
    try:
        result = await db.execute(
            select(TMSLayer).where(TMSLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # به‌روزرسانی فیلدها
        for field, value in layer_data.dict(exclude_unset=True).items():
            setattr(layer, field, value)
        
        await db.commit()
        await db.refresh(layer)
        
        return TMSLayerResponse.from_orm(layer)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در به‌روزرسانی لایه: {str(e)}")


@router.delete("/layers/{layer_id}")
async def delete_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """حذف لایه TMS"""
    try:
        result = await db.execute(
            select(TMSLayer).where(TMSLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # حذف منطقی
        layer.is_active = False
        await db.commit()
        
        return {"message": "لایه با موفقیت حذف شد"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در حذف لایه: {str(e)}")


@router.get("/layers/{layer_id}/info")
async def get_layer_info(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """دریافت اطلاعات تفصیلی لایه"""
    try:
        result = await db.execute(
            select(TMSLayer).where(TMSLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # اطلاعات لایه منبع
        source_info = None
        if layer.source_layer_id:
            source_result = await db.execute(
                select(ShapefileLayer).where(ShapefileLayer.id == layer.source_layer_id)
            )
            source_layer = source_result.scalar_one_or_none()
            if source_layer:
                source_info = {
                    "id": source_layer.id,
                    "name": source_layer.name,
                    "file_path": source_layer.file_path,
                    "feature_count": source_layer.feature_count,
                    "geometry_type": source_layer.geometry_type,
                    "crs": source_layer.crs
                }
        
        return {
            "layer": TMSLayerResponse.from_orm(layer),
            "source": source_info,
            "tile_url_template": f"/api/v1/tms/{layer_id}/{{z}}/{{x}}/{{y}}.png"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت اطلاعات لایه: {str(e)}")
