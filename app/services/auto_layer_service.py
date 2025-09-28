"""
Auto Layer Service - ایجاد خودکار لایه‌ها
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.gis import TMSLayer
import logging

logger = logging.getLogger(__name__)


class AutoLayerService:
    """سرویس ایجاد خودکار لایه‌ها"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def analyze_table_for_auto_layers(self, table_name: str) -> List[Dict[str, Any]]:
        """تحلیل جدول برای ایجاد خودکار لایه‌ها"""
        
        try:
            # Get geometry type
            geom_type_query = text(f"""
                SELECT ST_GeometryType(geom) as geom_type
                FROM {table_name}
                WHERE geom IS NOT NULL
                LIMIT 1
            """)
            
            result = await self.db_session.execute(geom_type_query)
            geom_result = result.fetchone()
            geom_type = geom_result.geom_type if geom_result else None
            
            logger.info(f"تحلیل جدول {table_name} - نوع هندسه: {geom_type}")
            
            # For POINT tables - create single layer
            if geom_type and 'Point' in geom_type:
                return [{
                    "name": f"layer_{table_name}",
                    "title": f"لایه {table_name}",
                    "table_name": table_name,
                    "filter_condition": None,
                    "description": f"لایه نقطه‌ای {table_name}"
                }]
            
            # For LINE/POLYGON tables - analyze filter columns
            elif geom_type and ('Line' in geom_type or 'Polygon' in geom_type):
                # Check for common filter columns
                filter_columns = ['fclass', 'type', 'category', 'class', 'highway', 'waterway', 'landuse', 'amenity']
                
                for col in filter_columns:
                    # Check if column exists
                    col_check_query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name 
                        AND column_name = :col_name
                    """)
                    
                    col_result = await self.db_session.execute(col_check_query, {
                        "table_name": table_name,
                        "col_name": col
                    })
                    
                    if col_result.fetchone():
                        logger.info(f"فیلد {col} در جدول {table_name} یافت شد")
                        
                        # Get unique values
                        values_query = text(f"""
                            SELECT {col}, COUNT(*) as count
                            FROM {table_name}
                            WHERE {col} IS NOT NULL
                            GROUP BY {col}
                            ORDER BY count DESC
                            LIMIT 20
                        """)
                        
                        values_result = await self.db_session.execute(values_query)
                        values = values_result.fetchall()
                        
                        if len(values) > 1:
                            logger.info(f"{len(values)} مقدار مختلف در {col} یافت شد")
                            
                            # Create layers for each value
                            layers = []
                            for val in values:
                                if val.count > 0:  # Only create layers with data
                                    layer_name = f"layer_{table_name}_{val[0].lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')}"
                                    layers.append({
                                        "name": layer_name,
                                        "title": f"{val[0]} - {table_name}",
                                        "table_name": table_name,
                                        "filter_condition": f"{col} = '{val[0]}'",
                                        "description": f"لایه {val[0]} از {table_name} ({val.count} مورد)"
                                    })
                            
                            return layers
                
                # If no filter columns found, create single layer
                logger.info(f"هیچ فیلد فیلتر در {table_name} یافت نشد - ایجاد یک لایه")
                return [{
                    "name": f"layer_{table_name}",
                    "title": f"لایه {table_name}",
                    "table_name": table_name,
                    "filter_condition": None,
                    "description": f"لایه {table_name}"
                }]
            
            else:
                logger.warning(f"نوع هندسه نامشخص در {table_name}")
                return [{
                    "name": f"layer_{table_name}",
                    "title": f"لایه {table_name}",
                    "table_name": table_name,
                    "filter_condition": None,
                    "description": f"لایه {table_name}"
                }]
        
        except Exception as e:
            logger.error(f"خطا در تحلیل جدول {table_name}: {str(e)}")
            return []
    
    async def create_auto_layers_for_table(self, table_name: str) -> Dict[str, Any]:
        """ایجاد خودکار لایه‌ها برای جدول مشخص"""
        
        created_layers = []
        errors = []
        
        try:
            # Analyze table
            layers_config = await self.analyze_table_for_auto_layers(table_name)
            
            if not layers_config:
                errors.append(f"هیچ لایه‌ای برای جدول {table_name} ایجاد نشد")
                return {
                    "created_layers": created_layers,
                    "total_created": 0,
                    "errors": errors
                }
            
            # Create layers
            for layer_config in layers_config:
                try:
                    logger.info(f"ایجاد لایه: {layer_config['title']}")
                    
                    # Get feature count
                    if layer_config['filter_condition']:
                        count_query = text(f"SELECT COUNT(*) FROM {layer_config['table_name']} WHERE {layer_config['filter_condition']}")
                    else:
                        count_query = text(f"SELECT COUNT(*) FROM {layer_config['table_name']}")
                    
                    count_result = await self.db_session.execute(count_query)
                    feature_count = count_result.scalar()
                    
                    # Get bounds
                    if layer_config['filter_condition']:
                        bounds_query = text(f"""
                            SELECT 
                                ST_XMin(ST_Extent(geom)) as minx,
                                ST_YMin(ST_Extent(geom)) as miny,
                                ST_XMax(ST_Extent(geom)) as maxx,
                                ST_YMax(ST_Extent(geom)) as maxy
                            FROM {layer_config['table_name']} 
                            WHERE {layer_config['filter_condition']} AND geom IS NOT NULL
                        """)
                    else:
                        bounds_query = text(f"""
                            SELECT 
                                ST_XMin(ST_Extent(geom)) as minx,
                                ST_YMin(ST_Extent(geom)) as miny,
                                ST_XMax(ST_Extent(geom)) as maxx,
                                ST_YMax(ST_Extent(geom)) as maxy
                            FROM {layer_config['table_name']} 
                            WHERE geom IS NOT NULL
                        """)
                    
                    bounds_result = await self.db_session.execute(bounds_query)
                    bounds_row = bounds_result.fetchone()
                    
                    if bounds_row and bounds_row.minx is not None:
                        bounds = {
                            "minx": float(bounds_row.minx),
                            "miny": float(bounds_row.miny),
                            "maxx": float(bounds_row.maxx),
                            "maxy": float(bounds_row.maxy)
                        }
                        center = {
                            "lat": (bounds['miny'] + bounds['maxy']) / 2,
                            "lng": (bounds['minx'] + bounds['maxx']) / 2
                        }
                    else:
                        bounds = None
                        center = None
                    
                    # Create TMS layer
                    tms_layer = TMSLayer(
                        name=layer_config['name'],
                        title=layer_config['title'],
                        description=layer_config['description'],
                        table_name=layer_config['table_name'],
                        filter_condition=layer_config['filter_condition'],
                        min_zoom=0,
                        max_zoom=18,
                        bounds=bounds,
                        center=center,
                        crs='EPSG:4326',
                        is_active=True
                    )
                    
                    self.db_session.add(tms_layer)
                    await self.db_session.commit()
                    await self.db_session.refresh(tms_layer)
                    
                    created_layers.append({
                        "id": tms_layer.id,
                        "name": tms_layer.name,
                        "title": tms_layer.title,
                        "feature_count": feature_count
                    })
                    
                    logger.info(f"لایه {layer_config['title']} ایجاد شد: {feature_count} مورد")
                    
                except Exception as e:
                    error_msg = f"خطا در ایجاد لایه {layer_config['name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "created_layers": created_layers,
                "total_created": len(created_layers),
                "errors": errors
            }
        
        except Exception as e:
            error_msg = f"خطا در ایجاد لایه‌ها برای جدول {table_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return {
                "created_layers": created_layers,
                "total_created": 0,
                "errors": errors
            }
    
    async def auto_create_layers_for_all_tables(self) -> Dict[str, Any]:
        """ایجاد خودکار لایه‌ها برای تمام جداول جغرافیایی"""
        
        all_created_layers = []
        all_errors = []
        
        try:
            # Get all geographic tables
            tables_query = text("""
                SELECT tablename
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename NOT IN ('tms_layers', 'tile_cache', 'layer_styles', 'spatial_ref_sys')
                ORDER BY tablename
            """)
            
            result = await self.db_session.execute(tables_query)
            tables = result.fetchall()
            
            logger.info(f"{len(tables)} جدول جغرافیایی یافت شد")
            
            for table in tables:
                table_name = table.tablename
                logger.info(f"پردازش جدول: {table_name}")
                
                result = await self.create_auto_layers_for_table(table_name)
                
                all_created_layers.extend(result["created_layers"])
                all_errors.extend(result["errors"])
            
            return {
                "created_layers": all_created_layers,
                "total_created": len(all_created_layers),
                "errors": all_errors
            }
        
        except Exception as e:
            error_msg = f"خطا در ایجاد خودکار لایه‌ها: {str(e)}"
            all_errors.append(error_msg)
            logger.error(error_msg)
            return {
                "created_layers": all_created_layers,
                "total_created": 0,
                "errors": all_errors
            }
