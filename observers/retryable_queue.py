import asyncio
from collections import deque

class RetryableQueue:
    def __init__(self):
        self.queue = deque()
        self.ids_in_queue = set()
        self.__not_empty = asyncio.Condition()

    async def put(self, item:dict, front = False):

        async with self.__not_empty:
            item_id = item.get("_id") or item.get("user_id")
            if item_id in self.ids_in_queue:
                return

            if front:
                self.queue.appendleft(item)
            else:
                self.queue.append(item)
            
            self.ids_in_queue.add(item_id)
            self.__not_empty.notify()

    async def get(self) -> dict:

        async with self.__not_empty:
            while not self.queue:
                await self.__not_empty.wait()
            
            item = self.queue.popleft()
            item_id = item.get("_id") or item.get("user_id")
            self.ids_in_queue.discard(item_id)
            return item

    def __len__(self):
        return len(self.queue)