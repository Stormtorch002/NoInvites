from discord.ext import commands
import postgres
import discord
import asyncio
from typing import Union


def from_record(record):
    joins, leaves, bonus = record['joins'], record['leaves'], record['bonus']
    return joins - leaves + bonus


async def get_total_invites(user, guild):
    query = 'SELECT joins, leaves, bonus FROM invites WHERE guild_id = $1 AND member_id = $2'
    res = await postgres.fetchone(query, guild.id, user.id)
    return from_record(res)


async def update_ranks(member):
    invites = await get_total_invites(member, member.guild)
    query = 'SELECT role_id, invites FROM ranks ' \
            'WHERE guild_id = $1 AND invites <= $2 ORDER BY invites'
    res = await postgres.fetchall(query, member.guild.id, invites)
    ranks = [rank['role_id'] for rank in res]
    if ranks:

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

    query = 'SELECT role_id, invites FROM ranks ' \
            'WHERE guild_id = $1 AND invites > $2 ORDER BY invites'
    print('yo')
    res = await postgres.fetchall(query, member.guild.id, invites)
    ranks = [rank['role_id'] for rank in res]
    if not ranks:
        return
    roles = [member.guild.get_role(role_id) for role_id in ranks]
    roles = [role for role in roles if role in member.roles]
    await member.remove_roles(*roles)


class Ranks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['invites'])
    async def rank(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author
        query = 'SELECT joins, leaves, bonus FROM invites WHERE guild_id = $1 AND member_id = $2'
        res = await postgres.fetchone(query, ctx.guild.id, member.id)
        if not res:
            return await ctx.send('You have no invites.')

        total = await get_total_invites(member, member.guild)
        query = 'SELECT invites, role_id FROM ranks WHERE invites > $1 ORDER BY invites'
        res2 = await postgres.fetchone(query, total)
        text = ''
        if res2:
            role = ctx.guild.get_role(res2['role_id'])
            if role:
                remaining = res2['invites'] - total
                text = f'**{remaining}** Invites to {role.mention}'

        embed = discord.Embed(
            color=member.color,
            title=f'{total} Invites',
            description=f'**Joins:** `{res["joins"]}`\n'
                        f'**Leaves:** `{res["leaves"]}`\n'
                        f'**Bonuses:** `{res["bonus"]}`\n\n'
                        + text
        )
        embed.set_thumbnail(url=str(ctx.guild.icon_url_as(format='png')))
        embed.set_author(name=str(member), icon_url=str(member.avatar_url_as(format='png')))
        await update_ranks(member)
        await ctx.send(embed=embed)

    @commands.command(aliases=['leaderboard', 'top'])
    async def lb(self, ctx, page: int = 1):
        query = 'SELECT member_id, joins, leaves, bonus, ' \
                'RANK () OVER (ORDER BY joins - leaves + bonus DESC) rank ' \
                'FROM invites WHERE guild_id = $1 ORDER BY joins - leaves + bonus DESC'
        res = await postgres.fetchall(query, ctx.guild.id)
        if not res:
            return await ctx.send('No invites found.')
        invites = [res[i:i + 5] for i in range(0, len(res), 5)]
        total = len(invites)
        try:
            invites = invites[page - 1]
        except IndexError:
            return await ctx.send('That page does not exist.')
        desc = '\n\n'.join(
            [f'__**Rank {i["rank"]}**__\n<@{i["member_id"]}>\n`{from_record(i)}` Invites' for i in invites]
        )
        embed = discord.Embed(
            title=f'Invites Leaderboard',
            color=ctx.author.color,
            description=desc
        )
        embed.set_author(name=f'Page {page}/{total}', icon_url=str(ctx.guild.icon_url_as(format='png')))
        await ctx.send(embed=embed)

    @commands.command(aliases=['createrank'])
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
            role = await commands.RoleConverter().convert(ctx, role)
        except commands.BadArgument:
            return await ctx.send(f'Could not make a role out of `{role}`.')
        query = 'SELECT id FROM ranks WHERE role_id = $1'
        res = await postgres.fetchone(query, role.id)
        if res:
            return await ctx.send(f'An invite rank with `{role.name}` role already exists.')

        await ctx.send('How many invites do they need to get this rank?')
        try:
            invites = (await self.bot.wait_for('message', check=check, timeout=30)).content
        except asyncio.TimeoutError:
            return await ctx.send(f'{ctx.author.mention} wake up and try again')
        if not invites.isdigit() or int(invites) < 1:
            return await ctx.send(f'Invalid number of invites.')
        query = 'SELECT id FROM ranks WHERE invites = $1 AND guild_id = $2'
        res = await postgres.fetchone(query, int(invites), ctx.guild.id)
        if res:
            return await ctx.send(f'An invite rank with `{invites}` invites already exists.')

        query = 'INSERT INTO ranks (guild_id, invites, role_id) VALUES ($1, $2, $3)'
        await postgres.execute(query, ctx.guild.id, int(invites), role.id)
        await ctx.send(f'Created invite rank with role `{role.name}` and needs {invites} invites.')

    @commands.command(aliases=['removerank'])
    @commands.has_guild_permissions(administrator=True)
    async def delrank(self, ctx, *, arg: Union[discord.Role, int]):
        if isinstance(arg, int):
            query = 'SELECT id FROM ranks WHERE guild_id = $1 AND invites = $2'
            res = await postgres.fetchone(query, ctx.guild.id, arg)
            if not res:
                return await ctx.send(f'No rank with `{arg}` invites found.')
            query = 'DELETE FROM ranks WHERE id = $1'
            await postgres.execute(query, res['id'])
            await ctx.send(f'Deleted rank with `{arg}` invites.')
        else:
            query = 'SELECT id FROM ranks WHERE guild_id = $1 AND role_id = $2'
            res = await postgres.fetchone(query, ctx.guild.id, arg.id)
            if not res:
                return await ctx.send(f'No rank with role `{arg.name}` found.')
            query = 'DELETE FROM ranks WHERE id = $1'
            await postgres.execute(query, res['id'])
            await ctx.send(f'Deleted rank with role `{arg.name}`.')

    @commands.command(aliases=['bonus', 'add'])
    @commands.has_guild_permissions(administrator=True)
    async def addinvites(self, ctx, member: discord.Member, amount: int):
        if amount < 1:
            return await ctx.send('Amount of invites must be positive.')
        query = 'INSERT INTO invites (guild_id, member_id, joins, leaves, bonus) ' \
                'VALUES ($1, $2, $3, $3, $4) ON CONFLICT (guild_id, member_id) ' \
                'DO UPDATE SET bonus = invites.bonus + $4'
        await postgres.execute(query, ctx.guild.id, member.id, 0, amount)
        await update_ranks(member)
        await ctx.send(f'I gave **{amount}** extra invites to `{member}`.')

    @commands.command(aliases=['rem', 'remove', 'removeinvites'])
    @commands.has_guild_permissions(administrator=True)
    async def reminvites(self, ctx, member: discord.Member, amount: int):
        if amount < 1:
            return await ctx.send('Amount of invites must be positive.')
        query = 'INSERT INTO invites (guild_id, member_id, joins, leaves, bonus) ' \
                'VALUES ($1, $2, $3, $3, $4) ON CONFLICT (guild_id, member_id) ' \
                'DO UPDATE SET bonus = invites.bonus + $4'
        await postgres.execute(query, ctx.guild.id, member.id, 0, -amount)
        await update_ranks(member)
        await ctx.send(f'I removed **{amount}** extra invites from `{member}`.')


def setup(bot):
    bot.add_cog(Ranks(bot))
