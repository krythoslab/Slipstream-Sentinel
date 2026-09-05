import discord
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def is_dangerous_role(role: discord.Role) -> bool:
    perms = role.permissions
    return any([
        perms.administrator,
        perms.manage_guild,
        perms.manage_roles,
        perms.manage_channels,
        perms.ban_members,
        perms.kick_members,
        perms.manage_webhooks,
    ])


def top_role(member: discord.Member) -> discord.Role:
    return max(member.roles, key=lambda r: r.position)


def hierarchy_ok(actor: discord.Member, target: discord.Member) -> bool:
    if actor.id == target.id:
        return True
    return top_role(actor) > top_role(target)


def has_perm(interaction: discord.Interaction, *perms: str) -> bool:
    return any(getattr(interaction.user.guild_permissions, p, False) for p in perms)


def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner_id


async def safe_send(channel, content=None, embed=None, view=None):
    try:
        return await channel.send(content=content, embed=embed, view=view)
    except discord.Forbidden:
        return None


def parse_duration(text: str) -> int:
    import re
    match = re.match(r"(\d+)([hHmMdD])", text)
    if not match:
        raise ValueError("Invalid duration format")
    value, unit = int(match.group(1)), match.group(2).lower()
    if unit == "m":
        return value * 60
    if unit == "h":
        return value * 3600
    if unit == "d":
        return value * 86400
    raise ValueError("Invalid unit")
