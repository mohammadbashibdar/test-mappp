from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.crud.database_crud import DatabaseCRUD
from app.schemas.gis import TMSLayerResponse, Bounds, TMSLayerCreate

router = APIRouter(prefix="/database", tags=["Database"])


class TableInfoResponse(BaseModel):
    """پاسخ اطلاعات جدول"""
    name: str
    feature_count: int
    bounds: Optional[Dict[str, float]]
    srid: Optional[int]
    geometry_type: Optional[str]
    columns: List[Dict[str, Any]]


class CreateLayerRequest(BaseModel):
    """درخواست ایجاد لایه از جدول"""
    table_name: str
    layer_name: str
    title: Optional[str] = None


@router.get("/tables", response_model=List[Dict[str, Any]])
async def get_available_tables(db: AsyncSession = Depends(get_db)):
    """دریافت لیست جداول جغرافیایی موجود در دیتابیس"""
    try:
        crud = DatabaseCRUD(db)
        tables = await crud.get_available_tables()
        return tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت جداول: {str(e)}")


@router.get("/tables/{table_name}/info", response_model=TableInfoResponse)
async def get_table_info(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """دریافت اطلاعات تفصیلی یک جدول"""
    try:
        crud = DatabaseCRUD(db)
        info = await crud.get_table_info(table_name)
        
        if not info:
            raise HTTPException(status_code=404, detail="جدول یافت نشد")
        
        return TableInfoResponse(**info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت اطلاعات جدول: {str(e)}")


@router.get("/tables/{table_name}/bounds")
async def get_table_bounds(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """دریافت محدوده جغرافیایی جدول"""
    try:
        crud = DatabaseCRUD(db)
        bounds = await crud.get_table_bounds(table_name)
        
        if not bounds:
            raise HTTPException(status_code=404, detail="محدوده جغرافیایی یافت نشد")
        
        return bounds
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت محدوده: {str(e)}")


@router.post("/tables/{table_name}/create-layer", response_model=TMSLayerResponse)
async def create_layer_from_table(
    table_name: str,
    request: CreateLayerRequest,
    db: AsyncSession = Depends(get_db)
):
    """ایجاد لایه TMS از جدول دیتابیس"""
    try:
        crud = DatabaseCRUD(db)
        layer = await crud.create_tms_layer_from_table(
            table_name=table_name,
            layer_name=request.layer_name,
            title=request.title
        )
        return layer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد لایه: {str(e)}")


@router.get("/layers/discover")
async def discover_layers(db: AsyncSession = Depends(get_db)):
    """کشف و شناسایی تمام لایه‌های جغرافیایی موجود در دیتابیس"""
    try:
        crud = DatabaseCRUD(db)
        
        # دریافت جداول جغرافیایی
        tables = await crud.get_available_tables()
        
        # دریافت لایه‌های TMS موجود
        existing_layers = await crud.get_all_tms_layers()
        existing_table_names = {layer.table_name for layer in existing_layers if layer.table_name}
        
        # تحلیل جداول و ایجاد پیشنهادات لایه
        layer_suggestions = []
        for table in tables:
            table_name = table['name']
            
            # دریافت اطلاعات تفصیلی جدول
            table_info = await crud.get_table_info(table_name)
            
            # بررسی اینکه آیا لایه از این جدول وجود دارد
            has_existing_layer = table_name in existing_table_names
            
            suggestion = {
                "table_name": table_name,
                "table_info": table_info,
                "has_existing_layer": has_existing_layer,
                "suggested_layer_name": f"layer_{table_name}",
                "suggested_title": f"لایه {table_name}",
                "geometry_type": table_info.get('geometry_type', 'Unknown'),
                "feature_count": table_info.get('feature_count', 0),
                "bounds": table_info.get('bounds'),
                "srid": table_info.get('srid'),
                "is_ready_for_layer": table_info.get('feature_count', 0) > 0 and table_info.get('bounds') is not None
            }
            
            layer_suggestions.append(suggestion)
        
        return {
            "total_tables": len(tables),
            "existing_layers": len(existing_layers),
            "ready_for_layers": len([s for s in layer_suggestions if s['is_ready_for_layer']]),
            "suggestions": layer_suggestions,
            "existing_layers_detail": existing_layers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در کشف لایه‌ها: {str(e)}")


@router.post("/layers/bulk-create")
async def bulk_create_layers(
    table_names: List[str],
    db: AsyncSession = Depends(get_db)
):
    """ایجاد لایه‌های TMS از چندین جدول به صورت گروهی"""
    try:
        crud = DatabaseCRUD(db)
        created_layers = []
        errors = []
        
        for table_name in table_names:
            try:
                # بررسی وجود جدول
                table_info = await crud.get_table_info(table_name)
                if not table_info or table_info.get('feature_count', 0) == 0:
                    errors.append(f"جدول {table_name} خالی است یا وجود ندارد")
                    continue
                
                # ایجاد لایه
                layer_name = f"layer_{table_name}"
                title = f"لایه {table_name}"
                
                layer = await crud.create_tms_layer_from_table(
                    table_name=table_name,
                    layer_name=layer_name,
                    title=title
                )
                
                created_layers.append(layer)
                
            except Exception as e:
                errors.append(f"خطا در ایجاد لایه از جدول {table_name}: {str(e)}")
        
        return {
            "created_layers": created_layers,
            "total_created": len(created_layers),
            "errors": errors,
            "success": len(errors) == 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد گروهی لایه‌ها: {str(e)}")


@router.get("/layers", response_model=List[TMSLayerResponse])
async def get_tms_layers(db: AsyncSession = Depends(get_db)):
    """دریافت تمام لایه‌های TMS"""
    try:
        crud = DatabaseCRUD(db)
        layers = await crud.get_all_tms_layers()
        return layers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه‌ها: {str(e)}")


@router.get("/layers/{layer_id}", response_model=TMSLayerResponse)
async def get_tms_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """دریافت لایه TMS خاص"""
    try:
        crud = DatabaseCRUD(db)
        layer = await crud.get_tms_layer(layer_id)
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        return layer
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه: {str(e)}")


@router.delete("/layers/{layer_id}")
async def delete_tms_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """حذف لایه TMS"""
    try:
        crud = DatabaseCRUD(db)
        success = await crud.delete_tms_layer(layer_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        return {"message": "لایه با موفقیت حذف شد"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در حذف لایه: {str(e)}")


@router.get("/tables/{table_name}/features")
async def get_features_in_bounds(
    table_name: str,
    minx: float = Query(..., description="حداقل X"),
    miny: float = Query(..., description="حداقل Y"),
    maxx: float = Query(..., description="حداکثر X"),
    maxy: float = Query(..., description="حداکثر Y"),
    limit: int = Query(1000, description="حداکثر تعداد ویژگی‌ها"),
    db: AsyncSession = Depends(get_db)
):
    """دریافت ویژگی‌های موجود در محدوده مشخص"""
    try:
        crud = DatabaseCRUD(db)
        bounds = {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
        features = await crud.get_features_in_bounds(table_name, bounds, limit)
        return features
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت ویژگی‌ها: {str(e)}")


@router.get("/layers/{layer_id}/preview")
async def preview_layer(
    layer_id: int,
    z: int = Query(8, ge=0, le=18, description="سطح زوم"),
    x: int = Query(0, ge=0, description="مختصات X تایل"),
    y: int = Query(0, ge=0, description="مختصات Y تایل"),
    db: AsyncSession = Depends(get_db)
):
    """پیش‌نمایش لایه در تایل مشخص"""
    try:
        crud = DatabaseCRUD(db)
        layer = await crud.get_tms_layer(layer_id)
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # استفاده از سرویس TMS برای تولید تایل
        from app.services.tms_service import TMSService
        tms_service = TMSService(db)
        
        tile_data = await tms_service.get_tile(layer_id, z, x, y, "png")
        
        if not tile_data:
            from fastapi.responses import Response
            # تایل خالی
            from PIL import Image
            import io
            img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            tile_data = buffer.getvalue()
        
        from fastapi.responses import Response
        return Response(
            content=tile_data,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پیش‌نمایش لایه: {str(e)}")


@router.get("/layers/{layer_id}/info")
async def get_layer_detailed_info(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """دریافت اطلاعات تفصیلی لایه"""
    try:
        crud = DatabaseCRUD(db)
        layer = await crud.get_tms_layer(layer_id)
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # دریافت اطلاعات جدول منبع
        table_info = {}
        if layer.table_name:
            table_info = await crud.get_table_info(layer.table_name)
        
        return {
            "layer": layer,
            "source_table_info": table_info,
            "tile_url_template": f"/api/v1/direct-tms/tables/{layer.table_name}/{{z}}/{{x}}/{{y}}.png",
            "capabilities": {
                "min_zoom": layer.min_zoom,
                "max_zoom": layer.max_zoom,
                "bounds": layer.bounds,
                "center": layer.center,
                "crs": layer.crs
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت اطلاعات لایه: {str(e)}")


@router.get("/layers/{layer_id}/sample-data")
async def get_layer_sample_data(
    layer_id: int,
    limit: int = Query(10, ge=1, le=100, description="تعداد نمونه داده"),
    db: AsyncSession = Depends(get_db)
):
    """دریافت نمونه داده‌های لایه"""
    try:
        crud = DatabaseCRUD(db)
        layer = await crud.get_tms_layer(layer_id)
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        if not layer.table_name:
            raise HTTPException(status_code=400, detail="لایه منبع جدول ندارد")
        
        # دریافت نمونه داده‌ها
        sample_data = await crud.get_features_in_bounds(
            layer.table_name,
            layer.bounds or {"minx": -180, "miny": -90, "maxx": 180, "maxy": 90},
            limit
        )
        
        return {
            "layer_id": layer_id,
            "table_name": layer.table_name,
            "sample_count": len(sample_data),
            "sample_data": sample_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت نمونه داده: {str(e)}")


@router.post("/layers/auto-create")
async def auto_create_layers(db: AsyncSession = Depends(get_db)):
    """ایجاد خودکار لایه‌ها برای تمام جداول جغرافیایی"""
    try:
        from app.services.auto_layer_service import AutoLayerService
        service = AutoLayerService(db)
        
        result = await service.auto_create_layers_for_all_tables()
        
        return {
            "message": "لایه‌ها با موفقیت ایجاد شدند",
            "created_layers": result["created_layers"],
            "total_created": result["total_created"],
            "errors": result["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد خودکار لایه‌ها: {str(e)}")


@router.post("/layers/auto-create/{table_name}")
async def auto_create_layers_for_table(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """ایجاد خودکار لایه‌ها برای جدول مشخص"""
    try:
        from app.services.auto_layer_service import AutoLayerService
        service = AutoLayerService(db)
        
        result = await service.auto_create_layers_for_table(table_name)
        
        return {
            "message": f"لایه‌ها برای جدول {table_name} با موفقیت ایجاد شدند",
            "created_layers": result["created_layers"],
            "total_created": result["total_created"],
            "errors": result["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد لایه‌ها: {str(e)}")


@router.get("/health")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """بررسی سلامت اتصال به دیتابیس"""
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "message": "اتصال به دیتابیس برقرار است",
            "database": "PostgreSQL"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در اتصال به دیتابیس: {str(e)}")

