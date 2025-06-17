from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from datetime import datetime
from db.statuses import Status,DownloadStatus,WatermarkStatus,DoneStatus
from typing import Dict, List, Union
import logging

logger = logging.getLogger(__name__)


class AsyncDatabase:
    def __init__(self, db_name='file_bot'):
        try:
            self.client = AsyncIOMotorClient('mongodb://localhost:27017/')
            self.db = self.client[db_name]
            self.users_collection = self.db['users']
            logger.info(f"Connected to MongoDB database: {db_name}")

        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")


    def __call__(self, *args, **kwds):
        return self.users_collection

    async def add_user(self,id:int, 
                       username:str, 
                       first_name:str = None,
                       last_name:str = None,
                       config:dict = None
                ):
        
        if config is None:
            config = self.get_default_config()
            
            
        try:
            await self.users_collection.update_one(
                {"_id":id},
                {
                    "$setOnInsert":{
                        "createdDate": datetime.now(),        
                    },
                    "$set":{
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "config": config
                    }
                },
                upsert=True 
            )
            logger.info(f"User {id} added or updated")

        except PyMongoError as e:
            logger.error(f"Error adding user {id}: {e}")


    async def add_message(self, id: int, message: dict):
        """
        Добавляет файл пользователю, если файл с таким file_id ещё не был добавлен.
        Устанавливает processing_order, если он отсутствует.
        id: _id
        message: dict = {
            message_id: int
            processing_order: time
            status: Status
            files: list = [
                file_data: dict = {
                    "file_id": "fewfwfwftw4fgw4tw4",
                    "file_path": photo/31.jpg,
                }
                ...
            ]
        }
        """
        message["status"] = DownloadStatus.QUEUED.value
        message["processing_order"]=datetime.now()
        message["caption"] = None
        try:
            result = await self.users_collection.update_one(
                {"_id":id,
                 "messages.message_id": {"$ne":message["message_id"]}},
                {"$push":{
                    "messages":message
                }}
            )
            if result.modified_count>0:
                return {"user_id":id,"message": message}
            return None
        except PyMongoError as e:
            logger.error(f"Ошибка добавления сообщения пользователю {id}: {e}")
            return None
    

    async def update_fields(self, user_id: int,message_id:int, file_id: int, updated_fields: dict):
        """
        Обновляет произвольные поля файла по его file_id у пользователя с _id = user_id.
        
        :param user_id: Telegram ID пользователя
        :param message_id ID сообщения
        :param file_id: Идентификатор файла в списке files
        :param updated_fields: Словарь с ключами и новыми значениями, которые нужно изменить
        """
        if not updated_fields:
            return False

        try:
            set_fields = {
                f"messages.$[m].files.$[f].{k}": v 
                for k,v in updated_fields.items()
            }

            result = await self.users_collection.update_one(
                {"_id":user_id},
                {
                    "$set": set_fields
                },
                array_filters=[
                    {"m.message_id": message_id},
                    {"f.file_id": file_id}
                ]
            )

            return result.modified_count>0
        
        except PyMongoError as e:
            logger.error(f"update error: {e}")
            return False
        
    async def get_configuration(self, user_id:int) -> Dict|None:
        try:
            result = await self.users_collection.find_one(
                {"_id":user_id},
                {
                    "config": 1  
                }
            )

            if result:
                result["user_id"] = result["_id"]
                del result["_id"]  
            return result
        
        except PyMongoError as e:
            logger.error(f"Ошибка получения конфигурации: {e}")
            return None
        
    def get_default_config(self):
        return {
                    "text": "watermark",
                    "color": (250, 250, 250, 128),
                    "font_size": 60,
                    "font_family": "Arial",
                    "font_style": "normal",
                    "text_weight": "normal",
                    "line_spacing": 80,
                    "angle": 45,
                }


    async def update_configuration(self, user_id:int, key,value):
        try:

            result = await self.users_collection.update_one(
                {
                    "_id": user_id
                },
                {
                    "$set":{
                        f"config.{key}":value
                    }
                
                }
            )
            return result.modified_count > 0 

        except PyMongoError as e:
            logger.error(f"Ошибка при обновлении конфигурации '{key}' для пользователя {user_id}: {e}")
            return False
        
    async def update_status_message(self, 
                                    user_id:int, 
                                    message_id:int, 
                                    status: WatermarkStatus | DownloadStatus |DoneStatus, fields: dict=None):
        
        try: 
            if not isinstance(status,(WatermarkStatus, DownloadStatus,DoneStatus)):
                return False
            
            set_fields = {"messages.$.status":status.value}

            if fields:       
                set_fields.update({
                    f"messages.$.{k}": v 
                    for k,v in fields.items()
                })
            
            
            result = await self.users_collection.update_one(
                {"_id":user_id,
                "messages.message_id":message_id},
                {"$set": set_fields}
            )
            return result.modified_count > 0 
        
        except PyMongoError as e:
            logger.error(f"Updating status error: {e}")
            return False

    

    async def get_users_with_files_by_status(
        self, 
        statuses: Union[WatermarkStatus, DownloadStatus, List[Union[WatermarkStatus, DownloadStatus]]],
        limit: int = 1
    ) -> List[Dict]:
        """
        Возвращает список пользователей с файлами указанного статуса.
        
        :param status: Один или несколько статусов (WatermarkStatus или DownloadStatus)
        :param limit: Максимальное количество возвращаемых пользователей
        :return: Список словарей вида {
            "user_id": ...,
            "files": [...]  # Только файлы с искомым статусом
        }
        """
        try:

            if not isinstance(statuses,list):
                statuses = [statuses]

            if not isinstance(statuses[0],(WatermarkStatus, DownloadStatus)):
                raise ValueError("")

            status_value = [s.value for s in statuses]

            pipeline = [
                {"$unwind": "$messages"},
                {"$match": 
                {"messages.status": {"$in": status_value}} },
                {"$sort":{"messages.processing_order":1}},
                {
                    "$sort":{
                        "processing_order":1
                    }
                },
                {"$limit":limit},
                {"$project":{
                    "_id": 0,
                    "user_id": "$_id",
                    "message": "$messages"
                }}
            ]

            cursor = self.users_collection.aggregate(pipeline=pipeline)
            return await cursor.to_list(length=limit)
            
        except PyMongoError as e:
            logger.error(f"Update error for:{id}")
            return []




