import asyncpg 
import asyncio 
from config import POSTGRES_CONFIG

loop = asyncio.get_event_loop()


async def _connect():
    pool = await asyncpg.create_pool(**POSTGRES_CONFIG)
    return pool


_pool = loop.run_until_complete(_connect())


async def create_tables():

    queries = [
        '''CREATE TABLE IF NOT EXISTS prefixes (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT UNIQUE,
            "prefix" VARCHAR(16)
        )''',
        '''CREATE TABLE IF NOT EXISTS invites (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT,
            "member_id" BIGINT,
            "joins" INTEGER,
            "leaves" INTEGER,
            "bonus" INTEGER,
            UNIQUE (guild_id, member_id)
        )''',
        '''CREATE TABLE IF NOT EXISTS joins (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT,
            "member_id" BIGINT,
            "inviter_id" BIGINT
        )''',
        '''CREATE TABLE IF NOT EXISTS channels (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT,
            "channel_id" BIGINT,
            "message" TEXT,
            "type" SMALLINT,
            UNIQUE (channel_id, type)
        )''',  # for type, 1 is join, 0 is leave
        '''CREATE TABLE IF NOT EXISTS ranks (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT,
            "role_id" BIGINT,
            "invites" INTEGER
        )''',
        '''CREATE TABLE IF NOT EXISTS stack_guilds (
            "id" SERIAL PRIMARY KEY,
            "guild_id" BIGINT
        )'''
    ] 
    async with _pool.acquire() as con:
        for query in queries:
            await con.execute(query)


async def fetchone(query, *parameters):
    async with _pool.acquire() as con:
        res = await con.fetchrow(query, *parameters)
        return res


async def fetchall(query, *parameters):
    async with _pool.acquire() as con:
        res = await con.fetch(query, *parameters)
        return res


async def execute(query, *parameters):
    async with _pool.acquire() as con:
        status = await con.execute(query, *parameters)
        return status
