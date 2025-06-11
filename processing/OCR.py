
import aiohttp
import asyncio
import aiofiles
import logging
from asyncio import Semaphore


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OCR:

    def __init__(self,OCR_API_KEY:str,OCR_URL:str):
        self.OCR_API_KEY = OCR_API_KEY
        self.OCR_URL = OCR_URL

    async def __recognize_text_from_image(self,image:tuple):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession() as session:
            
            form_data = aiohttp.FormData()
            form_data.add_field('apikey', self.OCR_API_KEY)
            form_data.add_field('language', 'auto')
            form_data.add_field('OCREngine', '2')
            form_data.add_field('isTable', 'true')
            form_data.add_field('file', image[1], filename=image[0])
            
            try:
                async with session.get(self.OCR_URL, data=form_data) as response:
                    if response.status != 200:
                        logger.error(f"OCR API вернул ошибку {response.status} для файла {image[0]}")
                        return ""
                    response_data = await response.json()
            except Exception as e:
                logger.exception(f"Ошибка при запросе к OCR API для файла {image[0]}: {e}")
                return ""

            parsed_text = response_data.get('ParsedResults', [{}])[0].get('ParsedText', '')
            if not parsed_text:
                logger.warning(f"OCR API не вернул текст для файла {image[0]}")
                return ""

            return parsed_text.strip()
            
    
    def __wapper_text(self,text:str):
        return f"O\n{text}\nO"


    async def get_text_from_image(self,image_path: str):
        try:
            async with aiofiles.open(image_path, 'rb') as image_file:
                content = await image_file.read()
                image = (image_path, content)
                
            result = await self.__recognize_text_from_image(image)
            
            if result:
                wrapped_result = self.__wapper_text(result)
                logger.info(f"Успешно обработан файл {image_path}")
                return wrapped_result
            else:
                logger.warning(f"Не удалось распознать текст с изображения {image_path}")

        except Exception as e:
            logger.exception(f"Ошибка при обработке файла {image_path}: {e}")

