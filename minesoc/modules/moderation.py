# moderation.py
# All moderation commands here

import discord
from discord.ext import commands

from minesoc.utils import checks


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_permission(self, permissions: discord.Permissions, seperator="\n"):
        output = list()
        for perm in permissions:
            if perm[1]:
                output.append("+ " + perm[0].replace("_", " ").title())
        else:
            return seperator.join(output)

    @commands.group(invoke_without_command=True)
    async def role(self, ctx: commands.Context, *, role: discord.Role = None):
        """Role information"""
        role = role or ctx.author.top_role
        embed = discord.Embed(color=role.color, description=role.mention)
        embed.set_author(name=f"{role.name} ({role.id})")
        embed.add_field(name="Color / Colour", value=role.color)
        embed.add_field(name="Created", value=self.bot.format_datetime(role.created_at))
        if role.permissions.value:
            embed.add_field(name="Permissions", value="```diff\n" + self.format_permission(role.permissions) + "```",
                            inline=False)
        embed.add_field(name="Other",
                        value=f"Position: `{role.position}`\nHoist: {ctx.switch(role.hoist)}\n"
                              f"Mentionable: {ctx.switch(role.mentionable)}",
                        inline=False)

        await ctx.send(embed=embed)

    @role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(self, ctx: commands.Context, member: discord.Member, roles: commands.Greedy[discord.Role]):
        await member.add_roles(*roles, reason=f"Operation executed by {ctx.author} ({ctx.author.id})")
        await ctx.success(
            description=f"Added {'roles' if len(roles) > 1 else 'role'} "
                        f"{' | '.join([r.mention for r in roles])} to {member.mention}."
        )

    @role.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_remove(self, ctx: commands.Context, member: discord.Member, roles: commands.Greedy[discord.Role]):
        await member.remove_roles(*roles, reason=f"Operation executed by {ctx.author} ({ctx.author.id})")
        await ctx.success(
            description=f"Removed {'roles' if len(roles) > 1 else 'role'} "
                        f"{' | '.join([r.mention for r in roles])} from {member.mention}."
        )

    @role.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_delete(self, ctx: commands.Context, role: discord.Role):
        await role.delete(reason=f"Operation executed by {ctx.author} ({ctx.author.id})")
        await ctx.success(description=f"Deleted role {role.name}.")

    @role.command(name="create")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_create(self, ctx: commands.Context, name: str, permissions: int, color: discord.Color = None):
        permissions = discord.Permissions(permissions)
        role = await ctx.guild.create_role(name=name, permissions=permissions,
                                           color=color if color else discord.Color.default(),
                                           reason=f"Operation executed by {ctx.author} ({ctx.author.id})")
        await ctx.success(
            description=f"Created role {role.mention} with following permissions:\n"
                        f"```diff\n{self.format_permission(permissions)}```"
        )

    @commands.command()
    @checks.is_owner_or_has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason given."):
        await member.kick(reason=reason)
        await ctx.success(description=f"Kicked {member.mention} from the server.")

    @commands.command()
    @checks.is_owner_or_has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason given."):
        await member.ban(reason=reason)
        await ctx.success(description=f"Banned {member.mention} from the server.")

    @commands.command()
    @checks.is_owner_or_has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.Member, *, reason: str = "No reason given."):
        await member.unban(reason=reason)
        await ctx.success(description=f"Unbanned {member.mention} from the server.")

    @commands.command()
    @checks.is_owner_or_has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def hackban(self, ctx, user: int, *, reason: str = "No reason given."):
        await ctx.guild.ban(discord.Object(id=user), reason=reason)
        await ctx.success(description=f"Hackbanned user with the ID of `{user}` from the server.")


def setup(bot):
    bot.add_cog(Moderation(bot))
