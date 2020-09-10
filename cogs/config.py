from discord.ext import commands
import postgres
import discord 


class Config(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def changeprefix(self, ctx, new_prefix):
        new_prefix = new_prefix.lstrip()
        query = 'INSERT INTO prefixes (prefix, guild_id) VALUES ($1, $2) ' \
                'ON CONFLICT (guild_id) DO UPDATE SET prefix = $1'
        self.bot.prefixes[ctx.guild.id] = new_prefix
        await postgres.execute(query, new_prefix, ctx.guild.id)
        await ctx.send(f'Prefix changed to `{new_prefix}`.')
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def join(self, ctx, channel: discord.TextChannel, *, message):
        query = 'INSERT INTO channels (guild_id, channel_id, message, type) VALUES ($1, $2, $3, $4) ' \
                'ON CONFLICT (guild_id, type) DO UPDATE SET channel_id = $2, message = $3'
        await postgres.execute(query, ctx.guild.id, channel.id, message, 1)
        await ctx.send(f'Linked join messages to {channel.mention}.')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx, channel: discord.TextChannel, *, message):
        query = 'INSERT INTO channels (guild_id, channel_id, message, type) VALUES ($1, $2, $3, $4) ' \
                'ON CONFLICT (guild_id, type) DO UPDATE SET channel_id = $2, message = $3'
        await postgres.execute(query, ctx.guild.id, channel.id, message, 0)
        await ctx.send(f'Linked leave messages to {channel.mention}.')


def setup(bot):
    bot.add_cog(Config(bot))
