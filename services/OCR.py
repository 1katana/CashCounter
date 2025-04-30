from const import Const
import aiohttp
import asyncio
import aiofiles
import logging
from asyncio import Semaphore


semaphore = Semaphore(3) 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def recognize_text_from_image(image:tuple):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession() as session:
        
        form_data = aiohttp.FormData()
        form_data.add_field('apikey', Const.OCR_API_KEY)
        form_data.add_field('language', 'auto')
        form_data.add_field('OCREngine', '2')
        form_data.add_field('isTable', 'true')
        form_data.add_field('file', image[1], filename=image[0])
        
        try:
            async with session.get(Const.OCR_URL, data=form_data) as response:
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
        
        
def wapper_text(text:str):
    return f"O\n{text}\nO"


async def get_text_from_image(image_path: str):
    async with semaphore:
        try:
                async with aiofiles.open(image_path, 'rb') as image_file:
                    content = await image_file.read()
                    image = (image_path, content)
                    
                result = await recognize_text_from_image(image)
                
                if result:
                    wrapped_result = wapper_text(result)
                    logger.info(f"Успешно обработан файл {image_path}")
                    return wrapped_result
                else:
                    logger.warning(f"Не удалось распознать текст с изображения {image_path}")

        except Exception as e:
            logger.exception(f"Ошибка при обработке файла {image_path}: {e}")

async def main(image_paths):
    tasks = [get_text_from_image(image_path) for image_path in image_paths]
    return await asyncio.gather(*tasks)
    
if __name__ == "__main__":
    image_paths = [
        "images/dowload/1595227146122330398.jpg",
        "images/dowload/1655786266185834359.jpg",
    ]
    
    asyncio.run(main(image_paths))