from discord.ext import commands
import discord
import postgres
from cogs import ranks


class Listeners(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    async def track_invites(self, member):
        old_invites = sorted(self.invites[member.guild], key=lambda i: i.id)
        try:
            new_invites = sorted(await member.guild.invites(), key=lambda i: i.id)
        except discord.Forbidden:
            return None
        old_length = len(old_invites)
        new_length = len(new_invites)
        old_i = new_i = 0
        while old_i < old_length and new_i < new_length:
            if old_invites[old_i].id == new_invites[new_i].id:
                if old_invites[old_i].uses != new_invites[new_i].uses:
                    self.invites[member.guild] = new_invites
                    return new_invites[new_i]
                else:
                    old_i += 1
                    new_i += 1
            elif old_invites[old_i].id < new_invites[new_i].id:
                old_i += 1
            else:
                new_i += 1
        return None

    async def update_join_invites(self, invite, member):
        query = 'INSERT INTO joins (guild_id, member_id, inviter_id) VALUES ($1, $2, $3)'
        await postgres.execute(query, member.guild.id, member.id, invite.inviter.id)
        query = 'SELECT id FROM invites WHERE guild_id = $1 AND member_id = $2'
        res = await postgres.fetchone(query, member.guild.id, invite.inviter.id)
        if res:
            query = 'UPDATE invites SET joins = invites.joins + $1 WHERE guild_id = $2 AND member_id = $3'
            await postgres.execute(query, 1, member.guild.id, invite.inviter.id)
        else:
            query = 'INSERT INTO invites (guild_id, member_id, joins, leaves, bonus) ' \
                    'VALUES ($1, $2, $3, $4, $4)'
            uses = sum([i.uses for i in self.invites[member.guild] if i.inviter.id == invite.inviter.id])
            await postgres.execute(query, member.guild.id, invite.inviter.id, uses, 0)
        return await ranks.get_total_invites(invite.inviter, member.guild)

    async def send_member_message(self, member, inviter, invites, ch_type):
        query = 'SELECT channel_id, message FROM channels WHERE type = $1 AND guild_id = $2'
        res = await postgres.fetchone(query, ch_type, member.guild.id)
        if res:
            channel = self.bot.get_channel(res['channel_id'])
            replacements = {
                '{member.mention}': member.mention,
                '{inviter.mention}': inviter.mention,
                '{member}': str(member),
                '{inviter}': str(inviter),
                '{member.name}': member.name,
                '{inviter.name}': inviter.name,
                '{invites}': str(invites)
            }
            message = res['message']
            for r in replacements:
                message = message.replace(r, replacements[r])
            return await channel.send(message)

    @commands.Cog.listener()
    async def on_ready(self):
        print(discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(8)))
        for guild in self.bot.guilds:
            try:
                self.invites[guild] = await guild.invites()
                if 'VANITY_URL' in guild.features:
                    vanity = await guild.vanity_invite()
                    self.invites[guild].append(vanity)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            self.invites[guild] = await guild.invites()
            if 'VANITY_URL' in guild.features:
                vanity = await guild.vanity_invite()
                self.invites[guild].append(vanity)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invites[invite.guild].append(invite)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        invite = await self.track_invites(member)
        if invite:
            invites = await self.update_join_invites(invite, member)
            if invite.inviter.id in [m.id for m in member.guild.members]:
                inviter = member.guild.get_member(invite.inviter.id)
                await ranks.update_ranks(inviter)
            await self.send_member_message(member, invite.inviter, invites, 1)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        query = 'SELECT inviter_id FROM joins WHERE guild_id = $1 AND member_id = $2 ORDER BY id DESC'
        res = await postgres.fetchone(query, member.guild.id, member.id)
        if res:
            inviter_id = res['inviter_id']
            query = 'UPDATE invites SET leaves = leaves + $1 WHERE guild_id = $2 AND member_id = $3'
            await postgres.execute(query, 1, member.guild.id, inviter_id)
            inviter = self.bot.get_user(inviter_id)
            inviter = inviter or await self.bot.fetch_user(inviter_id)
            if inviter.id in [m.id for m in member.guild.members]:
                inviter = member.guild.get_member(inviter.id)
                await ranks.update_ranks(inviter)
            invites = await ranks.get_total_invites(inviter, member.guild)
            await self.send_member_message(member, inviter, invites, 0)

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

            await ctx.send(f'You do not have the following perms: `{perms}`. '
                           f'You need these to do `{ctx.prefix}{ctx.invoked_with}`.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'You are missing the `{error.param.name}` argument.')
        elif isinstance(error, commands.BadArgument):
            await ctx.send(error.args[0].replace('"', '`'))
        else:
            raise error


def setup(bot):
    bot.add_cog(Listeners(bot))
