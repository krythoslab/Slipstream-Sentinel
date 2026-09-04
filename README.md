# Slipstream Sentinel

Production-ready Discord bot for the Slipstream Motorsport Discord server.

## Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials.
4. Ensure the bot application exists in the Discord Developer Portal.
5. Enable the required intents in the Developer Portal:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
6. Invite the bot to the server with the following scopes:
   - `bot`
   - `applications.commands`
   Required permissions:
   - Send Messages
   - Embed Links
   - Manage Messages
   - Kick Members
   - Ban Members
   - Moderate Members
   - Read Message History
   - Use Slash Commands
7. Run the bot:
   ```bash
   python run.py
   ```
8. Slash commands will sync automatically to the configured guild.

## Configuration

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Bot token from Developer Portal |
| `CLIENT_ID` | Application client ID |
| `GUILD_ID` | Server ID for command sync |
| `WELCOME_CHANNEL_ID` | Channel ID for welcome messages |
| `MODLOG_CHANNEL_ID` | Channel ID for moderation logs |

## Commands

- `/ping` - Check latency
- `/about` - Bot information
- `/mod warn <member> [reason]` - Warn a member
- `/mod timeout <member> <minutes> [reason]` - Timeout a member
- `/mod kick <member> [reason]` - Kick a member
- `/mod ban <member> [reason]` - Ban a member
- `/mod unban <user_id> [reason]` - Unban a user
- `/mod purge <amount>` - Purge messages
- `/mod history <user>` - View moderation history
- `/automod_add <word>` - Add a banned word
- `/automod_remove <word>` - Remove a banned word
- `/automod_list` - List banned words
- `/welcome_set <channel>` - Set welcome channel

## Development

```bash
pip install -r requirements.txt
python run.py
```

## License

MIT
