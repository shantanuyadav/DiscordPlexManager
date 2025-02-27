# Discord Plex Bot

A Discord bot that simplifies Plex server management by handling user invitations, subscription tracking, and access control. Manage members, monitor payment status, track renewal dates, and import existing users through simple Discord commands.

## Features

- Invite users to your Plex server with subscription tracking
- Remove users from your Plex server
- Track subscription durations and payment information
- View upcoming subscription renewals
- Check individual subscription details
- Import existing Plex users into the system

## Requirements

- Python 3.8+
- discord.py 2.0+
- Supabase account for database storage
- Discord Bot Token
- Plex server with admin access

## Detailed Setup Guide

### 1. Clone the Repository

```bash
git clone <repository-url>
cd discord-plex-bot
```

### 2. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Navigate to the "Bot" tab and click "Add Bot"
4. Under the Token section, click "Copy" to copy your bot token
5. Enable the following Privileged Gateway Intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
6. Navigate to the OAuth2 > URL Generator tab
7. Select the following scopes:
   - `bot`
   - `applications.commands`
8. Select the following bot permissions:
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
9. Copy the generated URL and open it in your browser to invite the bot to your server

### 4. Supabase Setup

1. Create an account on [Supabase](https://supabase.com/)
2. Create a new project
3. Once your project is created, go to Settings > API to find your:
   - Project URL
   - Project API Key (use the "anon" public key)
4. Initialize your database by running the SQL commands in `database/schema.sql` in the Supabase SQL Editor

### 5. Configure Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
PLEX_USERNAME=your_plex_username
PLEX_PASSWORD=your_plex_password
```

### 6. Run the Bot

Start the bot with:

```bash
python bot.py
```

## Commands Reference

### Subscription Management

#### `/invite`
Invite a new user to your Plex server and track their subscription.

```
/invite <plexusername/email> <server name> <duration> <payment method> <payment id> <start date>
```

**Parameters:**
- `plexusername/email`: The Plex username or email of the user to invite
- `server name`: The name of your Plex server
- `duration`: Subscription duration (1_month, 3_months, 6_months, 12_months)
- `payment method`: Method of payment (e.g., PayPal, Venmo, Cash)
- `payment id`: Transaction ID or reference
- `start date`: Start date of subscription (YYYY-MM-DD)

**Example:**
```
/invite johndoe@example.com MyPlexServer 3_months PayPal TX123456 2023-01-15
```

#### `/remove`
Remove a user from your Plex server and delete their subscription.

```
/remove <plexusername/email>
```

**Example:**
```
/remove johndoe@example.com
```

#### `/renew`
Renew an existing user's subscription.

```
/renew <plexusername/email> <duration>
```

**Example:**
```
/renew johndoe@example.com 6_months
```

### Subscription Information

#### `/fetch_subscription`
View details about a specific user's subscription.

```
/fetch_subscription <plexusername/email>
```

**Example:**
```
/fetch_subscription johndoe@example.com
```

#### `/due_subscription`
Check all subscriptions due within the next 30 days.

```
/due_subscription
```

This command displays subscriptions categorized by urgency:
- 🔴 **CRITICAL** (0-2 days remaining)
- 🟡 **WARNING** (3-7 days remaining)
- 🟢 **NOTICE** (8-30 days remaining)

### User Management

#### `/import_users`
Import existing Plex users into the subscription system.

```
/import_users <server name> <duration> <start date>
```

**Example:**
```
/import_users MyPlexServer 1_month 2023-01-01
```

## Troubleshooting

### Common Issues

1. **Bot doesn't respond to commands**
   - Ensure the bot has proper permissions in your Discord server
   - Check if all required gateway intents are enabled
   - Verify your Discord token is correct in the `.env` file

2. **Database connection errors**
   - Confirm your Supabase URL and API key are correct
   - Check if the database tables have been properly created

3. **Plex authentication issues**
   - Verify your Plex credentials in the `.env` file
   - Ensure your Plex server is online and accessible

### Logs

Check the `discord-bot.log` file for detailed error information.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.