from discord.ext import commands 
import traceback
import jishaku

class Listeners(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot 

    @commands.Cog.listener()
    async def on_ready(self):
        print('welcome boi')
        self.bot.load_extension('jishaku')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.db.cursor() as cur:
            query = 'SELECT channel_id, message FROM channels WHERE type = ? AND guild_id = ?'
            await cur.execute(query, (1, member.guild.id))
            row = await cur.fetchone()

        if row:
            channel = self.bot.get_channel(cur[0])
            # stormtorch, is leaving channel and welcoming channel same channel? some server would want seperate channels you know.
        # ok yes we are here now
        
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.CommandNotFound):
            return 

        if isinstance(error, commands.MissingPermissions):
            perms = []
            for perm in error.missing_perms:
                perm = ' '.join([word.capitalize() for word in perm])
                perms.append(f'`{perm}`')
            perms = ', '.join(perms)

            await ctx.send(f'You dont have the following perms: `{perms}`. You need these to do `{ctx.prefix}{ctx.invoked_with}`.')
        else:
            etype = type(error)
            trace = error.__traceback__
            verbosity = 4
            lines = traceback.format_exception(etype, error, trace, verbosity)
            traceback_text = ''.join(lines)
            print(traceback_text)


def setup(bot):
    bot.add_cog(Listeners(bot))
