import asyncio
import logging
import functools


def retry_async(max_retries = 3, delay = 1.0, exceptions = (Exception,), logger:logging = None):
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempts in range(1, max_retries+1):
                try: 
                    return await func(*args,**kwargs)
                except exceptions as e:
                    if logger:
                        logger.warning(f"Попытка номер: {attempts} ОШИБКА: {e}")
                    if attempts == max_retries:
                        if logger:
                            logger.error(f"Все попытки {max_retries} завершились неудачей.")
                        raise

                    await asyncio.sleep(delay)

        return wrapper
    
    return decorator
