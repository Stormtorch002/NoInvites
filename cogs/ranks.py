from discord.ext import commands
import postgres
import discord
import asyncio


async def get_total_invites(member):
    query = 'SELECT joins, leaves, bonus FROM invites WHERE guild_id = $1 AND member_id = $2'
    res = await postgres.fetchone(query, member.guild.id, member.id)
    joins, leaves, bonus = res['joins'], res['leaves'], res['bonus']
    return joins - leaves + bonus


async def update_join_ranks(member):
    invites = get_total_invites(member)
    query = 'SELECT role_id, invites FROM ranks ' \
            'WHERE guild_id = $1 AND invites <= $2 ORDER BY invites'
    res = await postgres.fetchall(query, member.guild.id, invites)
    ranks = [rank['role_id'] for rank in res]
    if not ranks:
        return

    query = 'SELECT id FROM stack_guilds WHERE guild_id = $1'
    res = await postgres.fetchone(query, member.guild.id)
    stack = True if res else False

    if stack:
        roles = []
        for role_id in ranks:
            role = member.guild.get_role(role_id)
            if role:
                if role not in member.roles:
                    roles.append(role)
            else:
                query = 'DELETE FROM ranks WHERE role_id = $1'
                await postgres.execute(query, role_id)
        await member.add_roles(*roles)
    else:
        top_role_id = ranks[-1]
        top_role = member.guild.get_role(top_role_id)
        if top_role:
            if top_role not in member.roles:
                await member.add_roles(top_role)
        else:
            query = 'DELETE FROM ranks WHERE role_id = $1'
            await postgres.execute(query, top_role_id)
        ranks.remove(top_role_id)
        removed = []
        for role_id in ranks:
            role = member.guild.get_role(role_id)
            if role:
                if role in member.roles:
                    removed.append(role)
            else:
                query = 'DELETE FROM ranks WHERE role_id = $1'
                await postgres.execute(query, role_id)
        await member.remove_roles(*removed)


class Ranks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['invites'])
    async def rank(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author
        query = 'SELECT joins, leaves, bonus, ' \
                'RANK () OVER (ORDER BY joins - leaves + bonus) rank ' \
                'FROM invites WHERE guild_id = $1 AND member_id = $2'
        res = await postgres.fetchone(query, ctx.guild.id, member.id)
        if not res:
            return await ctx.send('You have no invites.')
        total = get_total_invites(res)
        embed = discord.Embed(
            color=member.color,
            title=f'You have {total} invites',
        )
        embed.set_author(name=str(member), icon_url=str(member.avatar_url_as(format='png')))
        embed.add_field(name='Rank', value=str(res['rank']))
        embed.add_field(name='Joins', value=str(res['joins']))
        embed.add_field(name='Leaves', value=str(res['leaves']))
        embed.add_field(name='Bonuses', value=str(res['bonus']))
        await update_join_ranks(member)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def addrank(self, ctx):

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send('What role should people get when they reach this rank?')

        try:
            role = (await self.bot.wait_for('message', check=check, timeout=30)).content
        except asyncio.TimeoutError:
            return await ctx.send(f'{ctx.author.mention} wake up and try again')

        try:
            role_id = (await commands.RoleConverter().convert(ctx, role)).id
        except commands.BadArgument:
            return await ctx.send(f'Could not make a role out of `{role}`.')

        await ctx.send('How many invites do they need to get this rank?')

        try:
            invites = (await self.bot.wait_for('message', check=check, timeout=30)).content
        except asyncio.TimeoutError:
            return await ctx.send(f'{ctx.author.mention} wake up and try again')

        if not invites.isdigit() or int(invites) < 1:
            return await ctx.send(f'Invalid number of invites.')

        query = 'INSERT INTO ranks (guild_id, invites, role_id) VALUES ($1, $2, $3)'
        await postgres.execute(query, ctx.guild.id, invites, role_id)
        await ctx.send(f'Created invite rank with role `{role.name}` and needs {invites} invites.')


def setup(bot):
    bot.add_cog(Ranks(bot))
