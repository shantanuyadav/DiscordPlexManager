# Handles user invitations to Plex servers
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database.db import db
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)

# Define choices outside the class
duration_choices = [
    app_commands.Choice(name="2 Days Trial", value="2_days"),
    app_commands.Choice(name="1 Month", value="1_month"),
    app_commands.Choice(name="3 Months", value="3_months"),
    app_commands.Choice(name="6 Months", value="6_months"),
    app_commands.Choice(name="12 Months", value="12_months")
]

payment_choices = [
    app_commands.Choice(name="PayPal", value="paypal"),
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="Other", value="other")
]

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.duration_choices = duration_choices
        self.payment_choices = payment_choices
        self.server_choices = []
        self.last_refresh_time = datetime.min
        # Cache refresh interval in seconds (5 minutes)
        self.refresh_interval = 300

    async def refresh_server_choices(self):
        # Only refresh if it's been more than refresh_interval since last refresh
        current_time = datetime.now()
        if (current_time - self.last_refresh_time).total_seconds() < self.refresh_interval and self.server_choices:
            return
            
        try:
            servers = await db.get_all_plex_servers()
            self.server_choices = [app_commands.Choice(name=server['server_name'], value=server['server_name']) for server in servers]
            self.last_refresh_time = current_time
        except Exception as e:
            logger.error(f"Error fetching server choices: {str(e)}")
            # Don't clear existing choices if there's an error
            if not self.server_choices:
                self.server_choices = []

    async def server_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        try:
            await self.refresh_server_choices()
            # Filter choices based on current input if provided
            if current:
                return [choice for choice in self.server_choices if current.lower() in choice.name.lower()]
            return self.server_choices
        except Exception as e:
            logger.error(f"Error in server_name_autocomplete: {str(e)}")
            return []

    async def start_date_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            choices = [app_commands.Choice(name="Today", value=today)]
            
            # If user is typing a custom date, add it as an option
            if current and current.strip():
                # Check if the input matches date format (partial or complete)
                if len(current) <= 10 and all(c.isdigit() or c == '-' for c in current):
                    choices.append(app_commands.Choice(name=f"Custom: {current}", value=current))
            
            return choices
        except Exception as e:
            logger.error(f"Error in start_date_autocomplete: {str(e)}")
            return []

    @app_commands.command(name='invite', description='Invite a user to Plex server')
    @app_commands.describe(
        discord_user='Discord user to associate with the subscription',
        plex_username='Plex username or email',
        server_name='Name of the Plex server',
        duration='Duration of subscription',
        payment_method='Method of payment',
        payment_id='Payment ID/reference',
        start_date='Start date of subscription'
    )
    @app_commands.autocomplete(server_name=server_name_autocomplete, start_date=start_date_autocomplete)
    @app_commands.choices(
        duration=duration_choices,
        payment_method=payment_choices
    )
    async def invite(self, interaction: discord.Interaction, 
                    discord_user: discord.Member,
                    plex_username: str, 
                    server_name: str, 
                    duration: app_commands.Choice[str], 
                    payment_method: app_commands.Choice[str],
                    payment_id: str,
                    start_date: str):
        try:
            # Validate input parameters
            if not plex_username or not '@' in plex_username:
                raise ValueError("Please provide a valid Plex username/email")

            if not payment_id or len(payment_id.strip()) == 0:
                raise ValueError("Payment ID cannot be empty")

            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD format")

            # Try to defer the response, but handle potential network issues
            try:
                await interaction.response.defer()
                response_method = interaction.followup.send
            except (discord.errors.NotFound, discord.errors.HTTPException) as e:
                logger.warning(f"Could not defer response: {str(e)}")
                response_method = interaction.response.send_message
            
            # Get server details with error handling
            try:
                server = await db.get_plex_server(server_name)
                if not server:
                    raise ValueError(f"Server '{server_name}' not found or is currently unavailable")
            except Exception as db_error:
                logger.error(f"Database error while fetching server: {str(db_error)}")
                raise ValueError(f"Failed to access server information: {str(db_error)}")
            
            # Check if user already has a subscription
            invite_link = None
            try:
                existing_subscription = await db.get_subscription(plex_username)
                if existing_subscription:
                    logger.info(f"User {plex_username} already has a subscription, keeping existing invitation")
                    # Don't remove the existing subscription from database
                    invite_link = "User already invited to Plex server"
                else:
                    # Only invite if not already subscribed
                    try:
                        from plex.plex_manager import invite_user_to_plex
                        invite_result = invite_user_to_plex(server['plex_url'], server['plex_token'], plex_username)
                        if not invite_result:
                            raise ValueError(f"Failed to invite {plex_username} to Plex server. Please verify the username/email")
                        
                        # Get the invitation link and user details
                        invite_link = None
                        # Update plex_username with the actual username from Plex API
                        if isinstance(invite_result, dict):
                            plex_username = invite_result.get('username', plex_username)
                            plex_email = invite_result.get('email')
                    except Exception as plex_error:
                        error_str = str(plex_error)
                        logger.error(f"Plex invitation error: {error_str}")
                        
                        # Check if this is the "already sharing" error
                        if "You're already sharing this server with" in error_str:
                            logger.info(f"User {plex_username} is already invited to Plex server")
                            invite_link = "User already invited to Plex server"
                        else:
                            # Format the error message to be more user-friendly
                            clean_error = self._format_plex_error(error_str)
                            raise ValueError(f"Plex invitation failed: {clean_error}")
            except ValueError as ve:
                # Re-raise ValueError to be caught by the outer try/except
                raise ve
            except Exception as e:
                logger.warning(f"Error checking existing subscription: {str(e)}")
                # Continue with invitation if we couldn't check subscription status
                try:
                    from plex.plex_manager import invite_user_to_plex
                    invite_result = invite_user_to_plex(server['plex_url'], server['plex_token'], plex_username)
                    if not invite_result:
                        raise ValueError(f"Failed to invite {plex_username} to Plex server. Please verify the username/email")
                    
                    # Get the invitation link and user details
                    invite_link = None
                    # Update plex_username with the actual username from Plex API
                    if isinstance(invite_result, dict):
                        plex_username = invite_result.get('username', plex_username)
                        plex_email = invite_result.get('email')
                except Exception as plex_error:
                    error_str = str(plex_error)
                    logger.error(f"Plex invitation error: {error_str}")
                    
                    # Check if this is the "already sharing" error
                    if "You're already sharing this server with" in error_str:
                        logger.info(f"User {plex_username} is already invited to Plex server")
                        invite_link = "User already invited to Plex server"
                    else:
                        # Format the error message to be more user-friendly
                        clean_error = self._format_plex_error(error_str)
                        raise ValueError(f"Plex invitation failed: {clean_error}")

            # Add subscription with error handling
            try:
                subscription_data = {
                    'plex_username': plex_username,
                    'discord_username': str(discord_user),
                    'server_name': server_name,
                    'duration': duration.value,
                    'payment_method': payment_method.value,
                    'payment_id': payment_id,
                    'start_date': start_date
                }
                
                # Add email if we got it from the Plex API
                if 'plex_email' in locals() and plex_email:
                    subscription_data['email'] = plex_email
                await db.add_subscription(subscription_data)
            except Exception as db_error:
                logger.error(f"Database error while adding subscription: {str(db_error)}")
                raise ValueError(f"Failed to save subscription details: {str(db_error)}")
            
            # Create success embed
            embed = discord.Embed(
                title="✨ Plex Server Invitation",
                color=discord.Color.green()
            )
            
            # Add user info
            embed.add_field(
                name="👤 Discord User",
                value=discord_user.mention,
                inline=False
            )
            
            embed.add_field(
                name="📧 Plex Username",
                value=plex_username,
                inline=False
            )
            
            # Add server info
            embed.add_field(
                name="🖥️ Server",
                value=server_name,
                inline=True
            )
            
            # Add duration info
            embed.add_field(
                name="⏱️ Duration",
                value=duration.name,
                inline=True
            )
            
            # Add payment info
            embed.add_field(
                name="💳 Payment Details",
                value=f"Method: {payment_method.name}\nID: {payment_id}",
                inline=False
            )
            
            # Add start date
            embed.add_field(
                name="📅 Start Date",
                value=start_date,
                inline=True
            )

            # Add invitation link if available
            if invite_link:
                embed.add_field(
                    name="🔗 Invitation Link",
                    value=invite_link,
                    inline=False
                )
            
            embed.set_footer(text="Use /fetch_subscription to view subscription details")
            
            await response_method(embed=embed)
        except ValueError as ve:
            # Handle expected errors with user-friendly messages
            error_embed = discord.Embed(
                title="❌ Invitation Error",
                description=str(ve),
                color=discord.Color.red()
            )
            error_embed.set_footer(text="Please check the details and try again")
            
            logger.warning(f"Validation error in invite command: {str(ve)}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except Exception as response_error:
                logger.error(f"Failed to send error response: {str(response_error)}")
                
        except Exception as e:
            # Handle unexpected errors
            error_embed = discord.Embed(
                title="⚠️ Unexpected Error",
                description="An unexpected error occurred while processing your request",
                color=discord.Color.dark_red()
            )
            error_embed.add_field(
                name="Error Details",
                value=str(e),
                inline=False
            )
            error_embed.set_footer(text="Please contact an administrator if this persists")
            
            logger.error(f"Error in invite command: {str(e)}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except Exception as response_error:
                logger.error(f"Failed to send error response: {str(response_error)}")

async def setup(bot):
    await bot.add_cog(Invite(bot))