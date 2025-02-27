# Imports users from Plex servers into the database
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database.db import db
from plex.plex_manager import get_all_users_from_server
from datetime import datetime
from cogs.due_subscription import chunk_embed_field

logger = logging.getLogger(__name__)

class ImportUsers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='import_all', description='Import users with library access from all Plex servers')
    async def import_all(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            status_embed = discord.Embed(
                title="🔄 Importing Users",
                description="Starting import process...",
                color=discord.Color.blue()
            )
            status_message = await interaction.followup.send(embed=status_embed)

            servers = await db.get_all_plex_servers()
            if not servers:
                raise ValueError("No Plex servers found in database")

            total_imported = 0
            total_skipped = 0
            no_access_skipped = 0
            errors = []

            for server in servers:
                try:
                    status_embed.description = f"Processing server: {server['server_name']}"
                    await status_message.edit(embed=status_embed)

                    users = get_all_users_from_server(server['plex_url'], server['plex_token'])
                    
                    for user in users:
                        try:
                            # Skip users without library access
                            if not user.get('library_access', False):
                                no_access_skipped += 1
                                continue

                            existing_sub = await db.get_subscription(user['email'])
                            
                            if not existing_sub:
                                subscription_data = {
                                    'plex_username': user['username'],
                                    'email': user['email'],
                                    'server_name': server['server_name'],
                                    'duration': '1_month',
                                    'start_date': datetime.now().strftime('%Y-%m-%d')
                                }
                                
                                await db.add_subscription(subscription_data)
                                total_imported += 1
                            else:
                                total_skipped += 1
                                
                        except Exception as user_error:
                            errors.append(f"Error processing user {user['username']}: {str(user_error)}")
                            logger.error(f"Error processing user: {str(user_error)}", exc_info=True)

                except Exception as server_error:
                    errors.append(f"Error processing server {server['server_name']}: {str(server_error)}")
                    logger.error(f"Error processing server: {str(server_error)}", exc_info=True)

            final_embed = discord.Embed(
                title="✅ Import Complete",
                color=discord.Color.green()
            )

            final_embed.add_field(
                name="📊 Statistics",
                value=f"Users Imported: {total_imported}\nUsers Skipped (Existing): {total_skipped}\nUsers Skipped (No Access): {no_access_skipped}",
                inline=False
            )

            if errors:
                error_text = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more errors"
                
                for name, value, inline in chunk_embed_field("⚠️ Errors", error_text, False):
                    final_embed.add_field(name=name, value=value, inline=inline)

            await status_message.edit(embed=final_embed)

        except Exception as e:
            logger.error(f"Error in import_all command: {str(e)}", exc_info=True)
            error_embed = discord.Embed(
                title="❌ Import Failed",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            if status_message:
                await status_message.edit(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(ImportUsers(bot))