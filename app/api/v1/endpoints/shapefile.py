from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import os
import shutil
from pathlib import Path

from app.core.database import get_db
from app.models.gis import ShapefileLayer
from app.schemas.gis import ShapefileLayerCreate, ShapefileLayerResponse
from app.services.shapefile_processor import ShapefileProcessor

router = APIRouter(prefix="/shapefile", tags=["Shapefile"])

# مسیر ذخیره فایل‌های shapefile
UPLOAD_DIR = Path("uploads/shapefiles")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ShapefileLayerResponse)
async def upload_shapefile(
    file: UploadFile = File(..., description="فایل shapefile (.shp)"),
    name: str = Form(..., description="نام لایه"),
    description: Optional[str] = Form(None, description="توضیحات لایه"),
    db: AsyncSession = Depends(get_db)
):
    """آپلود و پردازش فایل shapefile"""
    try:
        # بررسی فرمت فایل
        if not file.filename.lower().endswith('.shp'):
            raise HTTPException(status_code=400, detail="فایل باید از نوع .shp باشد")
        
        # ایجاد مسیر ذخیره
        layer_dir = UPLOAD_DIR / name
        layer_dir.mkdir(exist_ok=True)
        
        # ذخیره فایل اصلی
        shp_path = layer_dir / file.filename
        with open(shp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # پردازش فایل
        processor = ShapefileProcessor(db)
        
        # اعتبارسنجی
        is_valid, message = processor.validate_shapefile(str(shp_path))
        if not is_valid:
            # حذف فایل در صورت نامعتبر بودن
            shutil.rmtree(layer_dir)
            raise HTTPException(status_code=400, detail=f"فایل نامعتبر: {message}")
        
        # ایجاد لایه
        layer = await processor.process_shapefile(
            file_path=str(shp_path),
            layer_name=name,
            description=description
        )
        
        return ShapefileLayerResponse.from_orm(layer)
        
    except HTTPException:
        raise
    except Exception as e:
        # حذف فایل در صورت خطا
        if 'layer_dir' in locals() and layer_dir.exists():
            shutil.rmtree(layer_dir)
        raise HTTPException(status_code=500, detail=f"خطا در آپلود فایل: {str(e)}")


@router.post("/upload-complete")
async def upload_complete_shapefile(
    shp_file: UploadFile = File(..., description="فایل .shp"),
    shx_file: UploadFile = File(..., description="فایل .shx"),
    dbf_file: UploadFile = File(..., description="فایل .dbf"),
    prj_file: Optional[UploadFile] = File(None, description="فایل .prj (اختیاری)"),
    name: str = Form(..., description="نام لایه"),
    description: Optional[str] = Form(None, description="توضیحات لایه"),
    db: AsyncSession = Depends(get_db)
):
    """آپلود کامل فایل shapefile با تمام فایل‌های مرتبط"""
    try:
        # ایجاد مسیر ذخیره
        layer_dir = UPLOAD_DIR / name
        layer_dir.mkdir(exist_ok=True)
        
        # ذخیره فایل‌های اصلی
        files_to_save = [
            (shp_file, ".shp"),
            (shx_file, ".shx"),
            (dbf_file, ".dbf")
        ]
        
        if prj_file:
            files_to_save.append((prj_file, ".prj"))
        
        for file, extension in files_to_save:
            file_path = layer_dir / f"{name}{extension}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        # پردازش فایل
        processor = ShapefileProcessor(db)
        shp_path = layer_dir / f"{name}.shp"
        
        # اعتبارسنجی
        is_valid, message = processor.validate_shapefile(str(shp_path))
        if not is_valid:
            shutil.rmtree(layer_dir)
            raise HTTPException(status_code=400, detail=f"فایل نامعتبر: {message}")
        
        # ایجاد لایه
        layer = await processor.process_shapefile(
            file_path=str(shp_path),
            layer_name=name,
            description=description
        )
        
        return ShapefileLayerResponse.from_orm(layer)
        
    except HTTPException:
        raise
    except Exception as e:
        # حذف فایل در صورت خطا
        if 'layer_dir' in locals() and layer_dir.exists():
            shutil.rmtree(layer_dir)
        raise HTTPException(status_code=500, detail=f"خطا در آپلود فایل: {str(e)}")


@router.get("/layers", response_model=List[ShapefileLayerResponse])
async def get_shapefile_layers(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """دریافت لیست لایه‌های shapefile"""
    try:
        query = select(ShapefileLayer)
        if active_only:
            query = query.where(ShapefileLayer.is_active == True)
        
        result = await db.execute(query)
        layers = result.scalars().all()
        
        return [ShapefileLayerResponse.from_orm(layer) for layer in layers]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه‌ها: {str(e)}")


@router.get("/layers/{layer_id}", response_model=ShapefileLayerResponse)
async def get_shapefile_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """دریافت اطلاعات لایه shapefile"""
    try:
        result = await db.execute(
            select(ShapefileLayer).where(ShapefileLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        return ShapefileLayerResponse.from_orm(layer)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لایه: {str(e)}")


@router.delete("/layers/{layer_id}")
async def delete_shapefile_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """حذف لایه shapefile"""
    try:
        result = await db.execute(
            select(ShapefileLayer).where(ShapefileLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # حذف فایل‌ها
        layer_dir = Path(layer.file_path).parent
        if layer_dir.exists():
            shutil.rmtree(layer_dir)
        
        # حذف از دیتابیس
        await db.delete(layer)
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
            select(ShapefileLayer).where(ShapefileLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        # بررسی وجود فایل
        file_exists = os.path.exists(layer.file_path)
        
        # اطلاعات فایل
        file_info = None
        if file_exists:
            processor = ShapefileProcessor(db)
            try:
                file_info = processor.get_shapefile_info(layer.file_path)
            except Exception as e:
                file_info = {"error": str(e)}
        
        return {
            "layer": ShapefileLayerResponse.from_orm(layer),
            "file_exists": file_exists,
            "file_info": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت اطلاعات لایه: {str(e)}")


@router.post("/layers/{layer_id}/validate")
async def validate_layer(
    layer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """اعتبارسنجی لایه shapefile"""
    try:
        result = await db.execute(
            select(ShapefileLayer).where(ShapefileLayer.id == layer_id)
        )
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=404, detail="لایه یافت نشد")
        
        processor = ShapefileProcessor(db)
        is_valid, message = processor.validate_shapefile(layer.file_path)
        
        return {
            "is_valid": is_valid,
            "message": message,
            "file_path": layer.file_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در اعتبارسنجی لایه: {str(e)}")
