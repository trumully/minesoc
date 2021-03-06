import asyncio

from minesoc import client


async def async_main():
    bot = client.Minesoc()
    try:
        await bot.start()
    finally:
        await bot.close()


asyncio.run(async_main())
