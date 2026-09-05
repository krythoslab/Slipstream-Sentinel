import discord
from sentinel.utils import utcnow_iso


def info_embed(title: str, description: str = None, color: int = 0x0099ff) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.parse_time(utcnow_iso()))
    return embed


def success_embed(title: str, description: str = None) -> discord.Embed:
    return info_embed(title, description, 0x00ff00)


def error_embed(title: str, description: str = None) -> discord.Embed:
    return info_embed(title, description, 0xff0000)


def mod_case_embed(case: dict) -> discord.Embed:
    embed = discord.Embed(title=f"Case #{case['id']}", color=0xffaa00, timestamp=discord.utils.parse_time(case.get("created_at") or utcnow_iso()))
    embed.add_field(name="Action", value=case["action"], inline=True)
    embed.add_field(name="Target", value=f"<@{case['target_id']}>", inline=True)
    embed.add_field(name="Moderator", value=f"<@{case['moderator_id']}>", inline=True)
    if case.get("reason"):
        embed.add_field(name="Reason", value=case["reason"], inline=False)
    if case.get("duration_seconds"):
        embed.add_field(name="Duration", value=f"{case['duration_seconds']}s", inline=True)
    return embed
