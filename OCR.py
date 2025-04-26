import const
import aiohttp
import asyncio

async def recognize_text_from_image(image:tuple):
    
    async with aiohttp.ClientSession() as session:
        
        form_data = aiohttp.FormData()
        form_data.add_field('apikey', const.OCR_API_KEY)
        form_data.add_field('language', 'chs')
        form_data.add_field('OCREngine', 2)
        form_data.add_field('file', image[1], filename=image[0])
        
        async with session.post(const.OCR_API_URL, data=form_data) as response:
            response_data = await response.json()
            
            parsed_text = response_data.get('ParsedResults', [{}])[0].get('ParsedText', '')
            return parsed_text