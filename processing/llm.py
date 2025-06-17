from openai import AsyncOpenAI
import asyncio
from processing.decorators import retry_async



class LLM:
    def __init__(self,MODEL:str,BASE_URL:str,API_KEY:str,SYSTEM_PROMPT:str):
        self.MODEL = MODEL
        # self.BASE_URL = BASE_URL
        # self.API_KEY = API_KEY
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.client = AsyncOpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
        )

    @retry_async()
    async def ask_llm(self, user_message: str):
        completion = await self.client.chat.completions.create(
            extra_body={},
            model=self.MODEL,
            # temperature=0.0,
            messages=[
                self.SYSTEM_PROMPT,
                {"role": "user", "content": user_message}
            ]
        )
        return completion.choices[0].message.content

