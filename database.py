import asyncpg 
import asyncio 
from config import POSTGRES_CONFIG

loop = asyncio.get_event_loop()


async def create_tables():
    pool = await asyncpg.create_pool(**POSTGRES_CONFIG)
    queries = [
        '''CREATE TABLE IF NOT EXISTS prefixes (
            "id" SERIAL,
            "guild_id" BIGINT,
            "prefix" VARCHAR(16)
        )''',
        '''CREATE TABLE IF NOT EXISTS channels (
            "id" SERIAL,
            "guild_id" BIGINT,
            "channel_id" BIGINT,
            "message" TEXT,
            "type" SMALLINT
        )''' # for type, 1 is join, 0 is leave
    ] 
    async with pool.acquire as con:
        for query in queries:
            await con.execute(query)
    return pool

db = loop.run_until_complete(create_tables())
