from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import io
import json
from typing import List, Dict, Any
import mercantile
from PIL import Image, ImageDraw
import pyproj
from functools import partial

from app.core.database import get_db

router = APIRouter(prefix="/direct-tms", tags=["Direct TMS"])


@router.get("/tables/{table_name}/{z}/{x}/{y}.png")
async def get_direct_tile(
    table_name: str,
    z: int,
    x: int,
    y: int,
    db: AsyncSession = Depends(get_db)
):
    """تولید مستقیم تایل از جدول دیتابیس"""
    try:
        # بررسی محدوده زوم
        if z < 0 or z > 22:
            raise HTTPException(status_code=400, detail="سطح زوم نامعتبر")
        
        # بررسی محدوده تایل
        max_tile = 2 ** z
        if x < 0 or x >= max_tile or y < 0 or y >= max_tile:
            raise HTTPException(status_code=400, detail="مختصات تایل نامعتبر")
        
        # محاسبه محدوده تایل
        tile_bounds = _tile_to_bounds(x, y, z)
        
        # دریافت داده‌ها از دیتابیس
        features = await _get_features_in_bounds(db, table_name, tile_bounds)
        
        if not features:
            # تایل خالی
            img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            tile_data = buffer.getvalue()
        else:
            # تولید تصویر تایل
            tile_image = _render_tile_from_features(features, tile_bounds)
            buffer = io.BytesIO()
            tile_image.save(buffer, format='PNG')
            tile_data = buffer.getvalue()
        
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
        raise HTTPException(status_code=500, detail=f"خطا در تولید تایل: {str(e)}")


def _tile_to_bounds(x: int, y: int, z: int):
    """تبدیل مختصات تایل به محدوده جغرافیایی"""
    # محاسبه محدوده تایل در WGS84
    west, south, east, north = mercantile.bounds(x, y, z)
    
    return west, south, east, north


async def _get_features_in_bounds(db: AsyncSession, table_name: str, bounds):
    """دریافت ویژگی‌ها در محدوده مشخص"""
    west, south, east, north = bounds
    
    query = text(f"""
        SELECT ST_AsGeoJSON(geom) as geometry, *
        FROM {table_name}
        WHERE ST_Intersects(geom, ST_MakeEnvelope(:west, :south, :east, :north, 4326))
        LIMIT 1000
    """)
    
    result = await db.execute(query, {
        "west": west,
        "south": south,
        "east": east,
        "north": north
    })
    
    features = []
    for row in result.fetchall():
        feature = dict(row._mapping)
        features.append(feature)
    
    return features


def _render_tile_from_features(features, bounds):
    """رندر کردن تایل از ویژگی‌های دیتابیس"""
    west, south, east, north = bounds
    tile_size = 256
    
    # ایجاد تصویر
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # محاسبه مقیاس
    scale_x = tile_size / (east - west)
    scale_y = tile_size / (north - south)
    
    print(f"Rendering tile: bounds={bounds}, scale_x={scale_x}, scale_y={scale_y}")
    print(f"Features count: {len(features)}")
    
    # رندر کردن هر ویژگی
    for feature in features:
        try:
            # پارس کردن geometry از GeoJSON
            if 'geometry' in feature and feature['geometry']:
                geom_data = json.loads(feature['geometry'])
                geometry = _parse_geojson_geometry(geom_data)
                
                if geometry and not geometry.is_empty:
                    # تبدیل مختصات به پیکسل
                    pixel_coords = _geometry_to_pixels(geometry, west, south, east, north)
                    
                    # رسم بر اساس نوع هندسه
                    if geometry.geom_type == 'Point':
                        _draw_point(draw, pixel_coords, 10)  # سطح زوم ثابت
                        print(f"Drew point at: {pixel_coords}")
                    elif geometry.geom_type in ['LineString', 'MultiLineString']:
                        _draw_line(draw, pixel_coords, 10)
                        print(f"Drew line with {len(pixel_coords)} points")
                    elif geometry.geom_type in ['Polygon', 'MultiPolygon']:
                        _draw_polygon(draw, pixel_coords, 10)
                        print(f"Drew polygon with {len(pixel_coords)} rings")
        except Exception as e:
            print(f"خطا در رندر ویژگی: {str(e)}")
            continue
    
    return img


def _parse_geojson_geometry(geom_data):
    """پارس کردن geometry از GeoJSON"""
    try:
        from shapely.geometry import shape
        return shape(geom_data)
    except Exception as e:
        print(f"خطا در پارس geometry: {str(e)}")
        return None


def _geometry_to_pixels(geometry, west: float, south: float, east: float, north: float):
    """تبدیل هندسه به مختصات پیکسل"""
    tile_size = 256
    
    def transform_coords(coords):
        x = int((coords[0] - west) / (east - west) * tile_size)
        y = int((north - coords[1]) / (north - south) * tile_size)
        return (x, y)
    
    if geometry.geom_type == 'Point':
        return transform_coords(geometry.coords[0])
    elif geometry.geom_type == 'LineString':
        return [transform_coords(coord) for coord in geometry.coords]
    elif geometry.geom_type == 'Polygon':
        return [[transform_coords(coord) for coord in ring.coords] for ring in geometry.geoms]
    
    return []


def _draw_point(draw: ImageDraw.Draw, coords, z: int):
    """رسم نقطه"""
    if not coords:
        return
    
    x, y = coords
    size = max(3, min(8, 12 - z))  # اندازه بر اساس سطح زوم
    
    # دایره قرمز
    draw.ellipse([x-size, y-size, x+size, y+size], 
                fill="#FF0000",
                outline="#FFFFFF",
                width=1)


def _draw_line(draw: ImageDraw.Draw, coords, z: int):
    """رسم خط"""
    if len(coords) < 2:
        return
    
    width = max(1, min(3, 8 - z))  # عرض بر اساس سطح زوم
    
    for i in range(len(coords) - 1):
        draw.line([coords[i], coords[i+1]], 
                 fill="#0000FF",
                 width=width)


def _draw_polygon(draw: ImageDraw.Draw, coords, z: int):
    """رسم چندضلعی"""
    if not coords:
        return
    
    width = max(1, min(2, 6 - z))  # عرض خط بر اساس سطح زوم
    
    for ring in coords:
        if len(ring) < 3:
            continue
        
        # پر کردن
        draw.polygon(ring, fill="#00FF00")
        
        # خط مرزی
        draw.polygon(ring, outline="#000000", width=width)
