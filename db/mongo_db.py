from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from datetime import datetime
import logging
from db.statuses import Status,DownloadStatus,WatermarkStatus



logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s: %(message)s",
                    handlers=[logging.FileHandler("db.log"),
                              logging.StreamHandler()]) 



class AsyncDatabase:
    def __init__(self, db_name='file_bot'):
        try:
            self.client = AsyncIOMotorClient('mongodb://localhost:27017/')
            self.db = self.client[db_name]
            self.users_collection = self.db['users']
            logging.info(f"Connected to MongoDB database: {db_name}")
        except PyMongoError as e:
            logging.error(f"Failed to connect to MongoDB: {e}")


    def __call__(self, *args, **kwds):
        return self.users_collection

    async def add_user(self,id:int, 
                       username:str, 
                       first_name:str = None,
                       last_name:str = None,
                       config:dict = None
                ):
        
        if config is None:
            config = {
                        "text": "watermark",
                        "color": (255, 255, 255, 128),
                        "font_size": 20,
                        "font_family": "Arial",
                        "font_style": "normal",
                        "text_weight": "normal",
                        "line_spacing": 50,
                        "angle": 0,
                    }
            
            
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
            logging.info(f"User {id} added or updated")

        except PyMongoError as e:
            logging.error(f"Error adding user {id}: {e}")

        
     
    async def add_file_download(self, id: int, file_data: dict):
        """
        Добавляет файл пользователю, если файл с таким file_id ещё не был добавлен.
        Устанавливает processing_order, если он отсутствует.
        """
        try:
            file_id = file_data.get("file_id")
            if file_id is None:
                raise ValueError("file_data must contain file_id")
            
            # Добавление файла, если его ещё нет
            await self.users_collection.update_one(
                {
                    "_id": id,
                    "files_download": {
                        "$not": {
                            "$elemMatch": {"file_id": file_id}
                        }
                    }
                },
                {
                    "$push": {"files_download": file_data},
                }
            )
            await self.users_collection.update_one(
                {
                    "_id": id,
                    "$or": [
                        {"processing_order": {"$exists": False}},
                        {"processing_order": None}
                    ]
                },
                {
                    "$set": {"processing_order": datetime.now()}
                }
            )

            logging.info(f"File added for user id: {id}")
        
        except ValueError as e:
            logging.error(f"Validation error for user id {id}: {e}")
        except PyMongoError as e:
            logging.error(f"MongoDB error adding file for user id {id}: {e}")


    async def add_file_watermark(self, id:int, file_data:dict):
        """
        file_data: dict = {
            "file_id": "fewfwfwftw4fgw4tw4",
            "file_path": photo/31.jpg,
            "status": "watermark/error_done/DONE",
            "processing_time": start - datetime.now()
        }
        """
        try:
            file_id = file_data.get("file_id")
            if file_id is None:
                raise ValueError("file_data must contain file_id")
            
            # Добавление файла, если его ещё нет
            await self.users_collection.update_one(
                {
                    "_id": id,
                    "files_watermark": {
                        "$not": {
                            "$elemMatch": {"file_id": file_id}
                        }
                    }
                },
                {
                    "$push": {"files_watermark": file_data},
                }
            )
            await self.users_collection.update_one(
                {
                    "_id": id,
                    "$or": [
                        {"processing_order": {"$exists": False}},
                        {"processing_order": None}
                    ]
                },
                {
                    "$set": {"processing_order": datetime.now()}
                }
            )

            logging.info(f"File added for user id: {id}")
        
        except ValueError as e:
            logging.error(f"Validation error for user id {id}: {e}")
        except PyMongoError as e:
            logging.error(f"MongoDB error adding file for user id {id}: {e}")
        

    
    async def get_user_files_download(self,id:int):
        try:
            user = await self.users_collection.find_one({"_id": id})
            logging.info(f"Get user files_download for id:{id}")
            return user.get("files_download", []) if user else []
        except PyMongoError as e:
            logging.error(f"Get user files_download FAIL for id:{id}")
            return []
        
    async def get_user_files_watermark(self,id:int):
        try:
            user = await self.users_collection.find_one({"_id": id})
            logging.info(f"Get user files_watermark for id:{id}")
            return user.get("files_watermark", []) if user else []
        except PyMongoError as e:
            logging.error(f"Get user files_watermark FAIL for id:{id}")
            return []

    async def get_file_download_by_id(self,id:int, file_id:int):
        try:
            user = await self.users_collection.find_one({"_id": id, "files_download.file_id": file_id},{"files_download.$": 1})

            logging.info(f"Get file_download by id for id:{id}")
            if user and user.get("files_download"):
                return user["files_download"][0]
        except:
            logging.error(f"Get file_download by id FAIL for id:{id}")
        finally:
            return None
        
    async def get_file_watermark_by_id(self,id:int, file_id:int):
        try:
            user = await self.users_collection.find_one({"_id": id, "files_watermark.file_id": file_id},{"files_watermark.$": 1})

            logging.info(f"Get file_watermark by id for id:{id}")
            if user and user.get("files_watermark"):
                return user["files_download"][0]
        except:
            logging.error(f"Get file_watermark by id FAIL for id:{id}")
        finally:
            return None
        

    async def update_file_download_fields(self, user_id: int, file_id: int, updated_fields: dict):
        """
        Обновляет произвольные поля файла по его file_id у пользователя с _id = user_id.
        
        :param user_id: Telegram ID пользователя
        :param file_id: Идентификатор файла в списке files
        :param updated_fields: Словарь с ключами и новыми значениями, которые нужно изменить
        """
        if not updated_fields:
            return  

        set_fields = {f"files_download.$.{k}": v for k, v in updated_fields.items()}

        result = await self.users_collection.update_one(
            {"_id": user_id, "files_download.file_id": file_id},
            {"$set": set_fields}
        )
        return result.modified_count > 0
    

    async def update_file_watermark_fields(self, user_id: int, file_id: int, updated_fields: dict):
        """
        Обновляет произвольные поля файла по его file_id у пользователя с _id = user_id.
        
        :param user_id: Telegram ID пользователя
        :param file_id: Идентификатор файла в списке files
        :param updated_fields: Словарь с ключами и новыми значениями, которые нужно изменить
        """
        if not updated_fields:
            return  

        set_fields = {f"files_watermark.$.{k}": v for k, v in updated_fields.items()}

        result = await self.users_collection.update_one(
            {"_id": user_id, "files_watermark.file_id": file_id},
            {"$set": set_fields}
        )

        return result.modified_count > 0


    async def get_one_with_status(self, status: Status):
        query = None

        if isinstance(status, WatermarkStatus):
            query = {
                "files_watermark": {
                    "$elemMatch": {"status": status.value}
                }
            }

        elif isinstance(status, DownloadStatus):
            query = {
                "files_download": {
                    "$elemMatch": {"status": status.value}
                }
            }

        if query:
            return await self.users_collection.find_one(query, sort=[("processing_order", 1)])
        return None




    async def update_file_watermark_status(self,id:int, file_id:int, status:WatermarkStatus):
        try:
            await self.users_collection.update_one(
                {"_id": id, "files_watermark.file_id": file_id},
                {"$set": {"files_watermark.$.status": status}}
            )
            logging.error(f"Updated for:{id}")
        except PyMongoError as e:
            logging.error(f"Update error for:{id}")

    async def update_file_download_status(self,id:int, file_id:int, status:DownloadStatus):
        try:
            await self.users_collection.update_one(
                {"_id": id, "files_download.file_id": file_id},
                {"$set": {"files_download.$.status": status}}
            )
            logging.error(f"Updated for:{id}")
        except PyMongoError as e:
            logging.error(f"Update error for:{id}")