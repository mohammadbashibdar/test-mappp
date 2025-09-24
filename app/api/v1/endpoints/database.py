from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.crud.database_crud import DatabaseCRUD
from app.schemas.gis import TMSLayerResponse, Bounds

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
