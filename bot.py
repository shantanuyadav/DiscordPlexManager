# Main entry point for the Discord bot
import discord
from discord.ext import commands
import asyncio
import logging
from config import DISCORD_BOT_TOKEN, DEBUG_MODE
from database.db import db

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('discord-bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# Initialize the bot with intents
class PlexBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        self.initial_extensions = [
            'cogs.invite',
            'cogs.remove',
            'cogs.subscription',
            'cogs.due_subscription',
            'cogs.import_users'
        ]
    
    async def setup_hook(self):
        try:
            # Load cogs
            for extension in self.initial_extensions:
                try:
                    logger.info(f"Loading extension: {extension}")
                    await self.load_extension(extension)
                    logger.info(f"Successfully loaded extension: {extension}")
                except Exception as extension_error:
                    logger.error(f"Failed to load extension {extension}: {str(extension_error)}", exc_info=True)
                    raise
            logger.info("Finished loading extensions")
            
            # Sync commands with Discord
            logger.info("Syncing commands with Discord...")
            await self.tree.sync()
            logger.info("Successfully synced commands with Discord")
        except Exception as e:
            logger.error(f"Error in setup_hook: {str(e)}", exc_info=True)
    
    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """Sync slash commands with Discord"""
        try:
            logger.info("Manually syncing commands...")
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} commands")
            await ctx.send(f"Synced {len(synced)} commands")
        except Exception as e:
            logger.error(f"Error syncing commands: {str(e)}", exc_info=True)
            await ctx.send(f"Error syncing commands: {str(e)}")

async def main():
    try:
        bot = PlexBot()
        async with bot:
            logger.info("Starting bot...")
            await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)

if __name__ == '__main__':
    asyncio.run(main())