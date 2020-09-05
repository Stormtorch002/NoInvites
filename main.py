from discord.ext import commands 
from config import TOKEN 
import aiosqlite3
import asyncio

open('./main.db', 'a+') # creates if not exists 

async def load_prefixes():
    async with db.cursor() as cur:
        prefixes = {}
        query = 'SELECT guild_id, prefix FROM prefixes'
        await cur.execute(query)
        rows = await cur.fetchall()

        for row in rows:
            prefixes[row[0]] = row[1]
        
        return prefixes

cached_prefixes = loop.run_until_complete(load_prefixes())

def get_prefix(client, message):
    prefix = cached_prefixes.get(message.guild.id)
    prefix = prefix if prefix else 'ii!'
    return prefix

bot = commands.Bot(command_prefix=get_prefix)
bot.db = db
bot.prefixes = cached_prefixes # botvar with all cached prefixes
bot.load_extension('cogs.config')
bot.load_extension('cogs.listeners')

@bot.command()
async def stupid(ctx):
    await ctx.send('stormtorch is stupid :thumbsup:')

@bot.command()
async def rank(ctx):
    await ctx.send('ok listen boi you have no invites.')

bot.run(TOKEN)
# what was that?
