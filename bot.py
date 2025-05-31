from services.OCR import run_ocr
from services.llm import ask_llm
from services.watermark import add_watermark
import asyncio

image_paths = [
        "images/dowload/1595227146122330398.jpg",
        "images/dowload/1655786266185834359.jpg",
    ]

async def Main():
    
    checks = await run_ocr(image_paths)
    print("Checks: ", checks)
    
    ask_llm_result = await ask_llm("\n".join(check for check in checks if check))
    print("LLM Result: ", ask_llm_result)
    
asyncio.run(Main())