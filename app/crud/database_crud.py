from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.database_reader import DatabaseReader
from app.services.tms_service import TMSService
from app.models.gis import TMSLayer
from app.schemas.gis import TMSLayerCreate, TMSLayerResponse
import logging

logger = logging.getLogger(__name__)


class DatabaseCRUD:
    """CRUD operations for database tables"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.db_reader = DatabaseReader(db_session)
        self.tms_service = TMSService(db_session)
    
    async def get_available_tables(self) -> List[Dict[str, Any]]:
        """دریافت لیست جداول جغرافیایی موجود"""
        try:
            tables = await self.db_reader.get_available_tables()
            return tables
        except Exception as e:
            logger.error(f"خطا در دریافت جداول: {str(e)}")
            return []
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """دریافت اطلاعات تفصیلی جدول"""
        try:
            info = await self.db_reader.get_table_info(table_name)
            return info
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات جدول {table_name}: {str(e)}")
            return {}
    
    async def create_tms_layer_from_table(
        self, 
        table_name: str, 
        layer_name: str, 
        title: str = None
    ) -> TMSLayerResponse:
        """ایجاد لایه TMS از جدول دیتابیس"""
        try:
            tms_layer = await self.tms_service.create_tms_layer_from_database(
                table_name, layer_name, title
            )
            return TMSLayerResponse.from_orm(tms_layer)
        except Exception as e:
            logger.error(f"خطا در ایجاد لایه TMS: {str(e)}")
            raise
    
    async def get_all_tms_layers(self) -> List[TMSLayerResponse]:
        """دریافت تمام لایه‌های TMS"""
        try:
            from sqlalchemy import select
            result = await self.db_session.execute(
                select(TMSLayer).where(TMSLayer.is_active == True)
            )
            layers = result.scalars().all()
            return [TMSLayerResponse.from_orm(layer) for layer in layers]
        except Exception as e:
            logger.error(f"خطا در دریافت لایه‌های TMS: {str(e)}")
            return []
    
    async def get_tms_layer(self, layer_id: int) -> Optional[TMSLayerResponse]:
        """دریافت لایه TMS خاص"""
        try:
            from sqlalchemy import select
            result = await self.db_session.execute(
                select(TMSLayer).where(TMSLayer.id == layer_id)
            )
            layer = result.scalar_one_or_none()
            return TMSLayerResponse.from_orm(layer) if layer else None
        except Exception as e:
            logger.error(f"خطا در دریافت لایه TMS: {str(e)}")
            return None
    
    async def delete_tms_layer(self, layer_id: int) -> bool:
        """حذف لایه TMS"""
        try:
            from sqlalchemy import select
            result = await self.db_session.execute(
                select(TMSLayer).where(TMSLayer.id == layer_id)
            )
            layer = result.scalar_one_or_none()
            
            if layer:
                layer.is_active = False
                await self.db_session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"خطا در حذف لایه TMS: {str(e)}")
            return False
    
    async def get_table_bounds(self, table_name: str) -> Optional[Dict[str, float]]:
        """دریافت محدوده جغرافیایی جدول"""
        try:
            bounds = await self.db_reader.get_table_bounds(table_name)
            if bounds:
                return {
                    "minx": bounds[0],
                    "miny": bounds[1],
                    "maxx": bounds[2],
                    "maxy": bounds[3]
                }
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت محدوده جدول {table_name}: {str(e)}")
            return None
    
    async def get_features_in_bounds(
        self, 
        table_name: str, 
        bounds: Dict[str, float],
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """دریافت ویژگی‌های موجود در محدوده مشخص"""
        try:
            bounds_tuple = (bounds["minx"], bounds["miny"], bounds["maxx"], bounds["maxy"])
            features = await self.db_reader.get_features_in_bounds(table_name, bounds_tuple)
            return features[:limit]
        except Exception as e:
            logger.error(f"خطا در دریافت ویژگی‌ها: {str(e)}")
            return []
