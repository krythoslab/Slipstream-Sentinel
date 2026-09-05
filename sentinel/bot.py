import discord
from discord.ext import commands, tasks
from sentinel.config import CLIENT_ID
from sentinel.utils import utcnow_iso, utcnow
from sentinel.database import Database, init_db, migrate
from sentinel.cogs import core, autorole, welcome, leave, moderation, automod, verification, server, league, steward, reminders


class SentinelBot(commands.Bot):
    def __init__(self, db: Database):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = False
        super().__init__(command_prefix="!", intents=intents)
        self.db = db
        self._start = None

    async def setup_hook(self):
        self._start = utcnow()
        await self.db.connect()
        await init_db(self.db)
        await migrate(self.db)
        cogs = [
            core.Core(self),
            autorole.AutoRole(self),
            welcome.Welcome(self),
            leave.Leave(self),
            moderation.Moderation(self),
            automod.AutoMod(self),
            verification.Verification(self),
            server.Server(self),
            league.League(self),
            steward.Steward(self),
            reminders.Reminders(self),
        ]
        for cog in cogs:
            await self.add_cog(cog)
        await self.tree.sync()
        self.reminder_loop.start()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Guilds: {len(self.guilds)}")
        print(f"Commands registered: {len(self.tree.get_commands())}")
        for cmd in self.tree.get_commands():
            print(f"  /{cmd.name}")

    async def on_member_join(self, member: discord.Member):
        await self.get_cog("AutoMod").process_join(member)
        await self.get_cog("AutoRole").process_join(member)
        await self.get_cog("Verification").process_join(member)
        await self.get_cog("Welcome").process_join(member)

    async def on_member_remove(self, member: discord.Member):
        await self.get_cog("Leave").process_leave(member)

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        await self.get_cog("AutoMod").process_message(message)

    @tasks.loop(seconds=30)
    async def reminder_loop(self):
        now = utcnow_iso()
        rows = await self.db.fetch("SELECT * FROM reminders WHERE due_at <= ?", (now,))
        for row in rows:
            guild = self.get_guild(row["guild_id"])
            if not guild:
                continue
            channel = guild.get_channel(row["channel_id"])
            if not channel:
                continue
            try:
                await channel.send(f"Reminder for <@{row['user_id']}>: {row['content']}")
            except discord.Forbidden:
                pass
            await self.db.execute("DELETE FROM reminders WHERE id = ?", (row["id"],))

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.wait_until_ready()
