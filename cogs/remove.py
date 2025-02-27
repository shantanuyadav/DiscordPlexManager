# Handles user removal from Plex servers
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database.db import db
from plex.plex_manager import remove_user_from_plex

logger = logging.getLogger(__name__)

class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='remove', description='Remove a user from all Plex servers')
    @app_commands.describe(plex_username='Plex username or email to remove')
    async def remove(self, interaction: discord.Interaction, plex_username: str):
        try:
            # Try to defer the response, but handle potential network issues
            try:
                await interaction.response.defer()
                response_method = interaction.followup.send
            except (discord.errors.NotFound, aiohttp.client_exceptions.ClientOSError):
                # If defer fails due to network issues, we'll try to use the original response
                logger.warning("Could not defer response, attempting to use original response")
                response_method = interaction.response.send_message
            
            try:
                # Get all Plex servers
                servers = await db.get_all_plex_servers()
                if not servers:
                    await response_method("No Plex servers found in the database.", ephemeral=True)
                    return

                removal_results = []
                for server in servers:
                    try:
                        # Attempt to remove user from each server
                        remove_result = remove_user_from_plex(server['plex_url'], server['plex_token'], plex_username)
                        removal_results.append((server['server_name'], remove_result))
                    except Exception as server_error:
                        logger.error(f"Error removing user from server {server['server_name']}: {str(server_error)}", exc_info=True)
                        removal_results.append((server['server_name'], False))
                # Format results message with enhanced error handling
                embed = discord.Embed(
                    title="🔄 Plex Server Removal Status",
                    color=discord.Color.orange()
                )
                
                # Add user info with more details
                embed.add_field(
                    name="👤 User Information",
                    value=f"**Username:** {plex_username}",
                    inline=False
                )
                
                # Add removal status for each server with detailed information
                success_servers = []
                failed_servers = []
                
                for server_name, success in removal_results:
                    if success:
                        success_servers.append(server_name)
                        embed.add_field(
                            name=f"✅ {server_name}",
                            value="Successfully removed user from server",
                            inline=True
                        )
                    else:
                        failed_servers.append(server_name)
                        embed.add_field(
                            name=f"❌ {server_name}",
                            value="Failed to remove user - Please check server logs",
                            inline=True
                        )
                
                # Add summary section
                summary = []
                if success_servers:
                    summary.append(f"✅ Successfully removed from {len(success_servers)} server(s)")
                if failed_servers:
                    summary.append(f"❌ Failed to remove from {len(failed_servers)} server(s)")
                
                if summary:
                    embed.add_field(
                        name="📊 Summary",
                        value="\n".join(summary),
                        inline=False
                    )
                
                # Add detailed footer with next steps
                if failed_servers:
                    footer_text = "Some removals failed. Please check server logs or try again later."
                else:
                    footer_text = "User access has been successfully revoked from all specified servers."
                
                embed.set_footer(text=footer_text)
                
                await response_method(embed=embed)

            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}", exc_info=True)
                await response_method(f"Error: {str(db_error)}", ephemeral=True)
                    
        except Exception as e:
            logger.error(f"Error in remove command: {str(e)}", exc_info=True)
            # Try to respond if possible, but this might fail if the connection is completely lost
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
                else:
                    await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
            except Exception:
                logger.error("Could not send error response to user", exc_info=True)
                    
async def setup(bot):
    await bot.add_cog(Remove(bot))