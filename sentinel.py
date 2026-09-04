
import asyncio
import datetime
import os
import random
import re
import sqlite3
import sys
import time
from collections import defaultdict
from typing import Optional

import discord
from discord import app_commands
from discord.ext import tasks

# ─── Constants ────────────────────────────────────────────────────────────────
CLIENT_ID = 1545480902841339935
GUILD_ID = 1545179492815741059

FALLBACK_DISCORD_TOKEN = "MTU0NTQ4MDkwMjg0MTMzOTkzNQ.GdXzJl.xnHNMNokmVvURcgxkCfPrPUBAj0nLBI7Nda0pE"

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN") or FALLBACK_DISCORD_TOKEN
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set. Set the environment variable or edit FALLBACK_DISCORD_TOKEN in sentinel.py.")

DATA_DIR = os.environ.get("DATA_DIR")
if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, "sentinel.db")
else:
    for candidate in [os.path.dirname(os.path.abspath(__file__)), "/tmp", os.path.expanduser("~")]:
        try:
            test_path = os.path.join(candidate, "sentinel.db")
            f = open(test_path, "a")
            f.close()
            DB_PATH = test_path
            break
        except (OSError, PermissionError):
            continue
    else:
        raise RuntimeError("No writable directory found for SQLite database.")

# ─── Database ─────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            joined_at TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS moderation_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            duration_seconds INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS automod_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS welcome_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            channel_id INTEGER,
            message TEXT,
            dm_message TEXT,
            leave_channel_id INTEGER,
            leave_message TEXT
        );
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id INTEGER PRIMARY KEY,
            slowmode_channel_id INTEGER,
            slowmode_seconds INTEGER DEFAULT 0,
            locked_channels TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS league_drivers (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            team_id INTEGER,
            number INTEGER,
            country TEXT DEFAULT 'N/A',
            joined_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#0099ff',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            circuit TEXT,
            scheduled_at TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            points INTEGER DEFAULT 0,
            dnq INTEGER DEFAULT 0,
            dnf INTEGER DEFAULT 0,
            fastest_lap INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS steward_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            evidence TEXT,
            status TEXT DEFAULT 'open',
            penalty TEXT,
            closed_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            due_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def db_fetch(query, params=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows[0] if one and rows else rows

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid

# ─── Helpers ──────────────────────────────────────────────────────────────────

def member_top_role(member: discord.Member) -> discord.Role:
    return max(member.roles, key=lambda r: r.position)

def role_hierarchy_ok(actor: discord.Member, target: discord.Member) -> bool:
    return member_top_role(actor) > member_top_role(target)

def permission_or(interaction: discord.Interaction, *perms: str) -> bool:
    return any(getattr(interaction.user.guild_permissions, p, False) for p in perms)

def safe_send(channel, content=None, embed=None, view=None):
    async def _send():
        try:
            return await channel.send(content=content, embed=embed, view=view)
        except discord.Forbidden:
            pass
    asyncio.create_task(_send())

# ─── AutoMod ──────────────────────────────────────────────────────────────────

class AutoModEngine:
    def __init__(self):
        self.recent_messages: dict[int, list[tuple[float, str]]] = defaultdict(list)
        self.join_timestamps: dict[int, list[float]] = defaultdict(list)
        self.mention_counts: dict[int, int] = defaultdict(int)
        self.exempt_roles: dict[int, set[int]] = defaultdict(set)

    def is_exempt(self, member: discord.Member) -> bool:
        guild_id = member.guild.id
        for role in member.roles:
            if role.id in self.exempt_roles.get(guild_id, set()):
                return True
        return False

    async def process_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if self.is_exempt(message.author):
            return
        guild_id = message.guild.id
        events = []
        now = time.time()
        content = message.content or ""
        user_id = message.author.id

        # Spam / flooding
        self.recent_messages[user_id].append((now, content))
        cutoff = now - 10
        self.recent_messages[user_id] = [(t, m) for t, m in self.recent_messages[user_id] if t > cutoff]
        if len(self.recent_messages[user_id]) > 5:
            events.append("flooding")

        # Repeated messages
        recent = [m for t, m in self.recent_messages[user_id] if t > now - 60]
        if recent.count(content) >= 3:
            events.append("repeated_messages")

        # Excessive mentions
        if len(message.mentions) >= 5:
            events.append("mass_mentions")
            self.mention_counts[user_id] += 1

        # Invite / suspicious links
        link_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
        links = link_pattern.findall(content)
        for link in links:
            if "discord.gg/" in link or "discordapp.com/invite/" in link or "discord.com/invite/" in link:
                events.append("invite_link")
            elif re.search(r"(verify|login|account|steam|free.*nitro|prize)", link, re.IGNORECASE):
                events.append("suspicious_link")

        # Banned words (simple local list; can be extended)
        banned_words = ["scam", "phishing", "malware", "gore", "nsfw"]
        lowered = content.lower()
        for word in banned_words:
            if word in lowered:
                events.append("banned_word")
                break

        for event in events:
            db_execute(
                "INSERT INTO automod_events (guild_id, user_id, event_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (guild_id, user_id, event, f"channel_id={message.channel.id}", datetime.datetime.utcnow().isoformat())
            )
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"AutoMod: {message.author.mention} your message was removed ({event}).",
                delete_after=15
            )
            return

    async def process_join(self, member: discord.Member):
        guild_id = member.guild.id
        now = time.time()
        self.join_timestamps[guild_id].append(now)
        cutoff = now - 60
        self.join_timestamps[guild_id] = [t for t in self.join_timestamps[guild_id] if t > cutoff]
        if len(self.join_timestamps[guild_id]) >= 10:
            db_execute(
                "INSERT INTO automod_events (guild_id, user_id, event_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (guild_id, member.id, "join_spike", "10+ joins in 60s", datetime.datetime.utcnow().isoformat())
            )
            channel = member.guild.system_channel or member.guild.text_channels[0]
            await safe_send(channel, "Raid detected: rapid join spike. Enabling lockdown.")

# ─── Bot ──────────────────────────────────────────────────────────────────────

class Sentinel(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = False
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.automod = AutoModEngine()

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        init_db()
        await self.update_reminders()
        self.reminder_task.start()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Database: {DB_PATH}")
        print(f"Guild: {GUILD_ID}")

    async def on_member_join(self, member: discord.Member):
        await self.automod.process_join(member)
        row = db_fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (member.guild.id,), one=True)
        if not row or not row.get("enabled"):
            return
        if row.get("channel_id"):
            ch = member.guild.get_channel(row["channel_id"])
            if ch:
                msg = row.get("message", "Welcome {user}!")
                await safe_send(ch, msg.format(user=member.mention, server=member.guild.name))
        if row.get("dm_message"):
            try:
                await member.send(row["dm_message"].format(user=member.mention, server=member.guild.name))
            except discord.Forbidden:
                pass

    async def on_member_remove(self, member: discord.Member):
        row = db_fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (member.guild.id,), one=True)
        if not row or not row.get("enabled"):
            return
        if row.get("leave_channel_id"):
            ch = member.guild.get_channel(row["leave_channel_id"])
            if ch:
                msg = row.get("leave_message", "{user} has left.")
                await safe_send(ch, msg.format(user=member.mention, server=member.guild.name))

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        await self.automod.process_message(message)

    @tasks.loop(seconds=30)
    async def reminder_task(self):
        now = datetime.datetime.utcnow().isoformat()
        rows = db_fetch("SELECT * FROM reminders WHERE due_at <= ?", (now,))
        for row in rows:
            guild = self.get_guild(row["guild_id"])
            if not guild:
                continue
            channel = guild.get_channel(row["channel_id"])
            if not channel:
                continue
            await safe_send(channel, f"Reminder for <@{row['user_id']}>: {row['content']}")
            db_execute("DELETE FROM reminders WHERE id = ?", (row["id"],))

    async def update_reminders(self):
        pass

    @reminder_task.before_loop
    async def before_reminder_task(self):
        await self.wait_until_ready()


client = Sentinel()

# ─── Core Commands ─────────────────────────────────────────────────────────────

@client.tree.command(name="ping", description="Check bot latency", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    latency_ms = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency_ms}ms")

@client.tree.command(name="status", description="Bot status overview", guild=discord.Object(id=GUILD_ID))
async def status(interaction: discord.Interaction):
    uptime = datetime.datetime.utcnow() - getattr(client, "_start", datetime.datetime.utcnow())
    await interaction.response.send_message(
        f"Servers: {len(client.guilds)} | Uptime: {uptime} | Latency: {round(client.latency*1000)}ms"
    )

@client.tree.command(name="about", description="About Sentinel", guild=discord.Object(id=GUILD_ID))
async def about(interaction: discord.Interaction):
    embed = discord.Embed(title="Slipstream Sentinel", description="Discord moderation & league bot.", color=0x0099ff)
    embed.add_field(name="Prefix", value="Slash commands only", inline=True)
    embed.add_field(name="Guild", value=str(GUILD_ID), inline=True)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="help", description="Show help", guild=discord.Object(id=GUILD_ID))
async def help(interaction: discord.Interaction):
    commands = [
        "/ping", "/status", "/about", "/help",
        "/config welcome", "/config welcome disable",
        "/warn", "/warnings", "/unwarn",
        "/timeout", "/untimeout", "/kick", "/ban", "/unban", "/purge",
        "/lock", "/unlock", "/slowmode", "/history",
        "/announce", "/role give", "/role remove", "/serverinfo", "/userinfo", "/poll",
        "/league register", "/league team", "/league standings",
        "/steward report", "/steward cases", "/steward close",
        "/remind",
    ]
    await interaction.response.send_message("**Commands:**\n" + "\n".join(commands))

# ─── Server Config ─────────────────────────────────────────────────────────────

@client.tree.command(name="config", description="Server configuration", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(action="Action", channel="Channel", message="Message", seconds="Seconds")
async def config(interaction: discord.Interaction, action: str, channel: discord.TextChannel = None, message: str = None, seconds: int = 0):
    if not permission_or(interaction, "administrator", "manage_guild"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return

    guild_id = interaction.guild_id
    if action == "welcome":
        row = db_fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,), one=True)
        if not row:
            db_execute("INSERT INTO welcome_config (guild_id) VALUES (?)", (guild_id,))
        db_execute(
            "UPDATE welcome_config SET enabled = 1, channel_id = ?, message = ? WHERE guild_id = ?",
            (channel.id if channel else None, message, guild_id)
        )
        await interaction.response.send_message("Welcome configured.")
    elif action == "welcome-disable":
        db_execute("UPDATE welcome_config SET enabled = 0 WHERE guild_id = ?", (guild_id,))
        await interaction.response.send_message("Welcome disabled.")
    elif action == "set-dm-welcome":
        db_execute("UPDATE welcome_config SET dm_message = ? WHERE guild_id = ?", (message, guild_id))
        await interaction.response.send_message("DM welcome message set.")
    else:
        await interaction.response.send_message("Unknown action.", ephemeral=True)

# ─── Announce ──────────────────────────────────────────────────────────────────

@client.tree.command(name="announce", description="Send an announcement", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel to announce in", message="Announcement content")
async def announce(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not permission_or(interaction, "manage_messages", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    await safe_send(channel, f"**Announcement**\n{message}")
    await interaction.response.send_message("Announced.", ephemeral=True)

# ─── Role Management ───────────────────────────────────────────────────────────

@client.tree.command(name="role", description="Role management", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(action="give or remove", user="User", role="Role")
async def role(interaction: discord.Interaction, action: str, user: discord.Member, role: discord.Role):
    if not permission_or(interaction, "manage_roles", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("Role is too high.", ephemeral=True)
        return
    try:
        if action == "give":
            await user.add_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(f"Gave {role.name} to {user.mention}.")
        elif action == "remove":
            await user.remove_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(f"Removed {role.name} from {user.mention}.")
        else:
            await interaction.response.send_message("Use give or remove.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Forbidden.", ephemeral=True)

# ─── Server & User Info ────────────────────────────────────────────────────────

@client.tree.command(name="serverinfo", description="Server information", guild=discord.Object(id=GUILD_ID))
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=0x0099ff)
    embed.add_field(name="Members", value=str(g.member_count), inline=True)
    embed.add_field(name="Owner", value=str(g.owner), inline=True)
    embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="userinfo", description="User information", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    embed = discord.Embed(title=str(user), color=0x0099ff)
    embed.add_field(name="ID", value=str(user.id), inline=True)
    embed.add_field(name="Joined", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "N/A", inline=True)
    embed.add_field(name="Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="poll", description="Create a poll", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(question="Poll question", option_a="Option A", option_b="Option B", option_c="Option C", option_d="Option D")
async def poll(interaction: discord.Interaction, question: str, option_a: str, option_b: str, option_c: str = None, option_d: str = None):
    options = [option_a, option_b]
    if option_c:
        options.append(option_c)
    if option_d:
        options.append(option_d)
    emojis = ["🇦", "🇧", "🇨", "🇩"]
    desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
    embed = discord.Embed(title=question, description=desc, color=0x0099ff)
    msg = await safe_send(interaction.channel, embed=embed)
    if msg:
        for i in range(len(options)):
            try:
                await msg.add_reaction(emojis[i])
            except discord.Forbidden:
                pass
    await interaction.response.send_message("Poll created.", ephemeral=True)

# ─── Moderation ────────────────────────────────────────────────────────────────

@client.tree.command(name="warn", description="Warn a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User", reason="Reason")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
    if not permission_or(interaction, "moderate_members", "kick_members", "ban_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    if not role_hierarchy_ok(interaction.user, user):
        await interaction.response.send_message("Role hierarchy too low.", ephemeral=True)
        return
    db_execute(
        "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (user.id, interaction.guild_id, interaction.user.id, reason, datetime.datetime.utcnow().isoformat())
    )
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "warn", user.id, interaction.user.id, reason, datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Warned {user.mention}: {reason}")

@client.tree.command(name="warnings", description="List warnings for a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User")
async def warnings(interaction: discord.Interaction, user: discord.Member):
    rows = db_fetch("SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?", (user.id, interaction.guild_id))
    if not rows:
        await interaction.response.send_message("No warnings found.")
        return
    lines = [f"#{r['id']} by <@{r['moderator_id']}>: {r['reason']} ({r['created_at'][:10]})" for r in rows]
    await interaction.response.send_message("\n".join(lines[:10]))

@client.tree.command(name="unwarn", description="Remove a warning", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(warning_id="Warning ID")
async def unwarn(interaction: discord.Interaction, warning_id: int):
    row = db_fetch("SELECT * FROM warnings WHERE id = ?", (warning_id,), one=True)
    if not row:
        await interaction.response.send_message("Warning not found.", ephemeral=True)
        return
    if row["guild_id"] != interaction.guild_id:
        await interaction.response.send_message("Wrong guild.", ephemeral=True)
        return
    if not permission_or(interaction, "moderate_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    db_execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
    await interaction.response.send_message("Warning removed.")

@client.tree.command(name="timeout", description="Timeout a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User", minutes="Minutes", reason="Reason")
async def timeout(interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason provided."):
    if not permission_or(interaction, "moderate_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    if not role_hierarchy_ok(interaction.user, user):
        await interaction.response.send_message("Role hierarchy too low.", ephemeral=True)
        return
    duration = datetime.timedelta(minutes=minutes)
    await user.timeout(duration, reason=reason)
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, duration_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "timeout", user.id, interaction.user.id, reason, minutes * 60, datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Timed out {user.mention} for {minutes} minutes.")

@client.tree.command(name="untimeout", description="Remove timeout from a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User")
async def untimeout(interaction: discord.Interaction, user: discord.Member):
    if not permission_or(interaction, "moderate_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    await user.timeout(None)
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "untimeout", user.id, interaction.user.id, "Timeout removed", datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Timeout removed from {user.mention}.")

@client.tree.command(name="kick", description="Kick a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User", reason="Reason")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
    if not permission_or(interaction, "kick_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    if not role_hierarchy_ok(interaction.user, user):
        await interaction.response.send_message("Role hierarchy too low.", ephemeral=True)
        return
    await user.kick(reason=reason)
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "kick", user.id, interaction.user.id, reason, datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Kicked {user.mention}.")

@client.tree.command(name="ban", description="Ban a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User ID or mention", reason="Reason")
async def ban(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided."):
    if not permission_or(interaction, "ban_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    member = interaction.guild.get_member(user.id)
    if member and not role_hierarchy_ok(interaction.user, member):
        await interaction.response.send_message("Role hierarchy too low.", ephemeral=True)
        return
    await interaction.guild.ban(user, reason=reason)
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "ban", user.id, interaction.user.id, reason, datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Banned {user.mention}.")

@client.tree.command(name="unban", description="Unban a user", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user_id="User ID")
async def unban(interaction: discord.Interaction, user_id: str):
    if not permission_or(interaction, "ban_members", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    user = await client.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    db_execute(
        "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.guild_id, "unban", user.id, interaction.user.id, "Unbanned", datetime.datetime.utcnow().isoformat())
    )
    await interaction.response.send_message(f"Unbanned {user.mention}.")

@client.tree.command(name="purge", description="Delete messages", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(count="Number of messages")
async def purge(interaction: discord.Interaction, count: int):
    if not permission_or(interaction, "manage_messages", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    await interaction.response.defer()
    deleted = await interaction.channel.purge(limit=count)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

@client.tree.command(name="lock", description="Lock a channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel to lock")
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not permission_or(interaction, "manage_channels", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    channel = channel or interaction.channel
    role = interaction.guild.default_role
    await channel.set_permissions(role, send_messages=False)
    row = db_fetch("SELECT * FROM server_config WHERE guild_id = ?", (interaction.guild_id,), one=True)
    if not row:
        db_execute("INSERT INTO server_config (guild_id) VALUES (?)", (interaction.guild_id,))
    db_execute("UPDATE server_config SET locked_channels = COALESCE(locked_channels, '[]') || ? WHERE guild_id = ?", (f'"{channel.id}"', interaction.guild_id))
    await interaction.response.send_message(f"Locked {channel.mention}.")

@client.tree.command(name="unlock", description="Unlock a channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel to unlock")
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not permission_or(interaction, "manage_channels", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    channel = channel or interaction.channel
    role = interaction.guild.default_role
    await channel.set_permissions(role, send_messages=None)
    db_execute("UPDATE server_config SET locked_channels = REPLACE(locked_channels, ?, ?) WHERE guild_id = ?", (f'"{channel.id}"', "", interaction.guild_id))
    await interaction.response.send_message(f"Unlocked {channel.mention}.")

@client.tree.command(name="slowmode", description="Set slowmode", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel", seconds="Seconds")
async def slowmode(interaction: discord.Interaction, channel: discord.TextChannel = None, seconds: int = 0):
    if not permission_or(interaction, "manage_channels", "administrator"):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
        return
    channel = channel or interaction.channel
    await channel.edit(slowmode_delay=seconds)
    db_execute(
        "UPDATE server_config SET slowmode_channel_id = ?, slowmode_seconds = ? WHERE guild_id = ?",
        (channel.id, seconds, interaction.guild_id)
    )
    await interaction.response.send_message(f"Slowmode set to {seconds}s in {channel.mention}.")

@client.tree.command(name="history", description="User moderation history", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="User")
async def history(interaction: discord.Interaction, user: discord.Member):
    rows = db_fetch("SELECT * FROM moderation_actions WHERE target_id = ? AND guild_id = ?", (user.id, interaction.guild_id))
    if not rows:
        await interaction.response.send_message("No history.")
        return
    lines = [f"{r['action']} by <@{r['moderator_id']}>: {r['reason']} ({r['created_at'][:10]})" for r in rows]
    await interaction.response.send_message("\n".join(lines[:10]))

# ─── League ────────────────────────────────────────────────────────────────────

@client.tree.command(name="league", description="League management", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(action="register, team, standings")
async def league(interaction: discord.Interaction, action: str, name: str = None, number: int = None, team_name: str = None):
    if action == "register":
        db_execute(
            "INSERT OR REPLACE INTO league_drivers (user_id, guild_id, number, joined_at) VALUES (?, ?, ?, ?)",
            (interaction.user.id, interaction.guild_id, number, datetime.datetime.utcnow().isoformat())
        )
        if team_name:
            team = db_fetch("SELECT id FROM league_teams WHERE guild_id = ? AND name = ?", (interaction.guild_id, team_name), one=True)
            if team:
                db_execute("UPDATE league_drivers SET team_id = ? WHERE user_id = ?", (team["id"], interaction.user.id))
        await interaction.response.send_message("Registered as driver.")
    elif action == "team":
        if not name:
            await interaction.response.send_message("Provide a team name.", ephemeral=True)
            return
        db_execute(
            "INSERT INTO league_teams (guild_id, name, created_at) VALUES (?, ?, ?)",
            (interaction.guild_id, name, datetime.datetime.utcnow().isoformat())
        )
        await interaction.response.send_message(f"Team {name} created.")
    elif action == "standings":
        rows = db_fetch("""
            SELECT d.user_id, d.number, t.name as team_name,
                   COALESCE(SUM(r.points), 0) as points
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
    else:
        await interaction.response.send_message("Unknown action.", ephemeral=True)

# ─── Steward (Race Control) ────────────────────────────────────────────────────

@client.tree.command(name="steward", description="Race control", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(action="report, cases, close", target="Target user", reason="Reason", evidence="Evidence", case_id="Case ID")
async def steward(interaction: discord.Interaction, action: str, target: discord.User = None, reason: str = None, evidence: str = None, case_id: int = None):
    if action == "report":
        if not target or not reason:
            await interaction.response.send_message("Target and reason required.", ephemeral=True)
            return
        case_id = db_execute(
            "INSERT INTO steward_cases (guild_id, reporter_id, target_id, reason, evidence, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, target.id, reason, evidence, "open", datetime.datetime.utcnow().isoformat(), datetime.datetime.utcnow().isoformat())
        )
        await interaction.response.send_message(f"Case #{case_id} opened.")
    elif action == "cases":
        rows = db_fetch("SELECT * FROM steward_cases WHERE guild_id = ? ORDER BY id DESC LIMIT 10", (interaction.guild_id,))
        if not rows:
            await interaction.response.send_message("No cases.")
            return
        lines = [f"#{r['id']} {r['status']} <@{r['target_id']}>: {r['reason']}" for r in rows]
        await interaction.response.send_message("\n".join(lines))
    elif action == "close":
        if not case_id:
            await interaction.response.send_message("Case ID required.", ephemeral=True)
            return
        row = db_fetch("SELECT * FROM steward_cases WHERE id = ? AND guild_id = ?", (case_id, interaction.guild_id), one=True)
        if not row:
            await interaction.response.send_message("Case not found.", ephemeral=True)
            return
        db_execute("UPDATE steward_cases SET status = 'closed', closed_by = ?, updated_at = ? WHERE id = ?", (interaction.user.id, datetime.datetime.utcnow().isoformat(), case_id))
        await interaction.response.send_message(f"Case #{case_id} closed.")
    else:
        await interaction.response.send_message("Unknown action.", ephemeral=True)

# ─── Reminders ────────────────────────────────────────────────────────────────

@client.tree.command(name="remind", description="Set a reminder", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(what="What to remind you about", when="Duration e.g. 1h, 30m, 1d")
async def remind(interaction: discord.Interaction, what: str, when: str):
    match = re.match(r"(\d+)([hHmMdD])", when)
    if not match:
        await interaction.response.send_message("Invalid duration. Use 1h, 30m, or 1d.", ephemeral=True)
        return
    value, unit = int(match.group(1)), match.group(2).lower()
    if unit == "h":
        delta = datetime.timedelta(hours=value)
    elif unit == "m":
        delta = datetime.timedelta(minutes=value)
    elif unit == "d":
        delta = datetime.timedelta(days=value)
    else:
        await interaction.response.send_message("Invalid unit.", ephemeral=True)
        return
    due_at = (datetime.datetime.utcnow() + delta).isoformat()
    db_execute(
        "INSERT INTO reminders (user_id, guild_id, channel_id, content, due_at) VALUES (?, ?, ?, ?, ?)",
        (interaction.user.id, interaction.guild_id, interaction.channel_id, what, due_at)
    )
    await interaction.response.send_message(f"Reminder set for {when}: {what}")

# ─── Entry Point ───────────────────────────────────────────────────────────────

client._start = datetime.datetime.utcnow()
client.run(DISCORD_TOKEN)
