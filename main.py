from discord.ext import commands 
from config import TOKEN
import discord
import postgres
import asyncio


def jayti_or_stormtorch():
    def predicate(ctx):
        return ctx.message.author.id in (553058885418876928, 576187414033334282)
    return commands.check(predicate)


async def load_prefixes():
    await postgres.create_tables()
    prefixes = {}
    query = 'SELECT guild_id, prefix FROM prefixes'
    res = await postgres.fetchall(query)

    for row in res:
        prefixes[row[0]] = row[1]

    return prefixes

cached_prefixes = asyncio.get_event_loop().run_until_complete(load_prefixes())


def get_prefix(client, message):
    prefix = client.prefixes.get(message.guild.id)
    return '!'
    # prefix = prefix if prefix else '!'
    # return commands.when_mentioned_or(prefix)(client, message)


bot = commands.Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    activity=discord.Game("with miku's pp \U0001f633"),
    status=discord.Status.dnd,
    help_command=None
)
bot.prefixes = cached_prefixes  # botvar with all cached prefixes
cogs = (
    'cogs.config',
    'cogs.listeners',
    'cogs.ranks',
    # 'jishaku'
)
[bot.load_extension(cog) for cog in cogs]


@bot.command(name='help')
async def _help(ctx):
    await ctx.send('<https://docs.google.com/document/d/1X2rvN_TEAtOiNBfhMjc40DnexJVQcxWsun-oBC5wqks/edit>')


@bot.command()
async def stupid(ctx):
    await ctx.send('stormtorch is stupid :thumbsup:')


@bot.command(name='eval')
@jayti_or_stormtorch()
async def _eval(ctx, *, code):
    code = '\n'.join([f'    {line}' for line in code.splitlines()])
    exec(
        f'async def __ex(ctx, bot):\n' +
        code
    )
    try:
        await locals()['__ex'](ctx, bot)
        await ctx.message.add_reaction('\U00002705')
    except Exception as e:
        await ctx.send(f'```diff\n- {e}```')

if __name__ == '__main__':
    bot.run(TOKEN)
