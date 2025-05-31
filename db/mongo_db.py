from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from datetime import datetime
import logging

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

    async def add_user(self,id:int, 
                       username:str, 
                       first_name:str = None,
                       last_name:str = None,
                       config:dict = None
                ):
        
        config if config else {
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
                        "config": config
                    },
                    "$set":{
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name
                    }
                },
                upsert=True 
            )
            logging.info(f"User {id} added or updated")

        except PyMongoError as e:
            logging.error(f"Error adding user {id}: {e}")

        
        
    async def add_file(self, id:int, file_data:dict):
        try:
            await self.users_collection.update_one(
            {"_id":id},
            {
                "$push":{"files":file_data},
                "$set": {"processing_order":datetime.now()}
            }
            )

            logging.info(f"Files added for user id:{id}")
        except PyMongoError as e:
            logging.error(f"Files added FAIL for user id:{id}")
    
        
    async def get_user_files(self,id:int):
        try:
            user = await self.users_collection.find_one({"_id": id})
            logging.info(f"Get user files for id:{id}")
            return user.get("files", []) if user else []
        except PyMongoError as e:
            logging.error(f"Get user files FAIL for id:{id}")
            return []

    async def get_file_by_id(self,id:int, file_id:int):
        try:
            user = await self.users_collection.find_one({"_id": id, "files.file_id": file_id},{"files.$": 1})

            logging.info(f"Get file by id for id:{id}")
            if user and user.get("files"):
                return user["files"][0]
        except:
            logging.error(f"Get file by id FAIL for id:{id}")
        finally:
            return None

    async def update_file_status(self,id:int, file_id:int, status:str):
        try:
            await self.users_collection.update_one(
                {"_id": id, "files.file_id": file_id},
                {"$set": {"files.$.status": status}}
            )
            logging.error(f"Updated for:{id}")
        except PyMongoError as e:
            logging.error(f"Update error for:{id}")
