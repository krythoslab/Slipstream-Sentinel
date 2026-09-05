import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed


class League(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="league-register", description="Register as a driver")
    @app_commands.describe(number="Driver number", team_name="Team name (optional)")
    async def league_register(self, interaction: discord.Interaction, number: int = None, team_name: str = None):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO league_drivers (user_id, guild_id, number, joined_at) VALUES (?, ?, ?, ?)",
            (interaction.user.id, interaction.guild_id, number, utcnow_iso())
        )
        if team_name:
            team = await self.bot.db.fetch(
                "SELECT id FROM league_teams WHERE guild_id = ? AND name = ?", (interaction.guild_id, team_name), one=True
            )
            if team:
                await self.bot.db.execute(
                    "UPDATE league_drivers SET team_id = ? WHERE user_id = ?", (team["id"], interaction.user.id)
                )
        await interaction.response.send_message("Registered as driver.")

    @app_commands.command(name="league-team", description="Create a team")
    @app_commands.describe(name="Team name")
    async def league_team(self, interaction: discord.Interaction, name: str):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "INSERT INTO league_teams (guild_id, name, created_at) VALUES (?, ?, ?)",
            (interaction.guild_id, name, utcnow_iso())
        )
        await interaction.response.send_message(embed=success_embed("Team created", f"Team {name} created."))

    @app_commands.command(name="league-standings", description="Show league standings")
    async def league_standings(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch("""
            SELECT d.user_id, d.number, t.name as team_name, COALESCE(SUM(r.points), 0) as points
            FROM league_drivers d
            LEFT JOIN league_teams t ON d.team_id = t.id
            LEFT JOIN league_results r ON r.driver_id = d.user_id
            WHERE d.guild_id = ?
            GROUP BY d.user_id
            ORDER BY points DESC
            LIMIT 20
        """, (interaction.guild_id,))
        if not rows:
            await interaction.response.send_message("No standings yet.")
            return
        lines = [f"#{i+1} <@{r['user_id']}> ({r['team_name'] or 'N/A'}): {r['points']} pts" for i, r in enumerate(rows)]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="league-season", description="Create or manage a season")
    @app_commands.describe(name="Season name", active="Set active")
    async def league_season(self, interaction: discord.Interaction, name: str, active: bool = True):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "INSERT INTO league_seasons (guild_id, name, active, created_at) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, name, int(active), utcnow_iso())
        )
        if active:
            await self.bot.db.execute(
                "UPDATE league_seasons SET active = 0 WHERE guild_id = ? AND name != ?",
                (interaction.guild_id, name)
            )
        await interaction.response.send_message(embed=success_embed("Season created", f"Season '{name}' {'active' if active else 'inactive'}."))
