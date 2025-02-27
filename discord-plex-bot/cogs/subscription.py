# Fetches subscription details
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database.db import db
from datetime import datetime
from utils.date_utils import calculate_end_date

logger = logging.getLogger(__name__)

class Subscription(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='fetch_subscription', description='Fetch subscription details')
    @app_commands.describe(
        user_identifier='Discord username, Plex username, or Plex email to check'
    )
    async def fetch_subscription(self, interaction: discord.Interaction, user_identifier: str):
            try:
                # Defer the response since this might take a while
                await interaction.response.defer()
                
                # Check if the input is a Discord mention (<@id>) and convert it to username
                if user_identifier.startswith('<@') and user_identifier.endswith('>'):
                    user_id = user_identifier.strip('<@!>')
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        user_identifier = f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name
                    except:
                        # If we can't fetch the user, continue with the original identifier
                        pass
                    
                # Get subscription details from database
                # Try to find by discord username first
                subscriptions = await db.get_subscription_by_discord(user_identifier)
                if not subscriptions:
                    # If not found, try by plex username/email
                    subscriptions = await db.get_subscription(user_identifier)
                
                if not subscriptions:
                    raise ValueError(f"No subscription found for user {user_identifier}")
                
                # Handle multiple subscriptions
                if len(subscriptions) > 1:
                    # Create an embed for multiple subscriptions
                    embed = discord.Embed(
                        title="📺 Multiple Plex Subscriptions Found",
                        description=f"Found {len(subscriptions)} subscriptions for {user_identifier}",
                        color=discord.Color.blue()
                    )
                    
                    for i, details in enumerate(subscriptions, 1):
                        # Calculate end date
                        start_date = datetime.strptime(details['start_date'], '%Y-%m-%d')
                        end_date = calculate_end_date(start_date, details['duration'])
                        days_remaining = (end_date - datetime.now()).days
                        
                        # Add status emoji
                        status = "🟢" if days_remaining > 7 else "🟡" if days_remaining > 2 else "🔴"
                        
                        # Add field for each subscription
                        embed.add_field(
                            name=f"Subscription #{i}: {details['plex_username']}",
                            value=f"Server: {details['server_name']}\n"
                                  f"Duration: {details['duration'].replace('_', ' ').title()}\n"
                                  f"End Date: {end_date.strftime('%Y-%m-%d')}\n"
                                  f"Remaining: {status} {days_remaining} days",
                            inline=False
                        )
                    
                    await interaction.followup.send(embed=embed)
                    return
                
                # Format subscription details for a single subscription
                details = subscriptions[0]
                
                # Calculate end date
                start_date = datetime.strptime(details['start_date'], '%Y-%m-%d')
                end_date = calculate_end_date(start_date, details['duration'])
                days_remaining = (end_date - datetime.now()).days
                
                # Rest of the code remains the same
                # Create embed
                embed = discord.Embed(
                    title="📺 Plex Subscription Details",
                    color=discord.Color.blue()
                )
                
                # Add user info
                embed.add_field(
                    name="👤 Plex User",
                    value=details['plex_username'],
                    inline=False
                )

                # Add Discord user info if available
                if 'discord_username' in details and details['discord_username']:
                    embed.add_field(
                        name="👥 Discord User",
                        value=details['discord_username'],
                        inline=False
                    )
                
                # Add server info
                embed.add_field(
                    name="🖥️ Server",
                    value=details['server_name'],
                    inline=True
                )
                
                # Add duration info
                embed.add_field(
                    name="⏱️ Duration",
                    value=details['duration'].replace('_', ' ').title(),
                    inline=True
                )
                
                # Add dates
                embed.add_field(
                    name="📅 Start Date",
                    value=details['start_date'],
                    inline=True
                )
                embed.add_field(
                    name="📅 End Date",
                    value=end_date.strftime('%Y-%m-%d'),
                    inline=True
                )
                
                # Add days remaining with appropriate color indicator
                status = "🟢" if days_remaining > 7 else "🟡" if days_remaining > 2 else "🔴"
                embed.add_field(
                    name="⏳ Time Remaining",
                    value=f"{status} {days_remaining} days",
                    inline=True
                )
                
                # Add payment info
                if 'payment_method' in details and 'payment_id' in details:
                    embed.add_field(
                        name="💳 Payment Info",
                        value=f"Method: {details['payment_method']}\nID: {details['payment_id']}",
                        inline=False
                    )
                
                # Add footer
                embed.set_footer(text="Use /due_subscription to see all upcoming renewals")
                
                await interaction.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"Error in fetch_subscription command: {str(e)}", exc_info=True)
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name='renew', description='Renew a user\'s Plex subscription')
    @app_commands.describe(
        user_identifier='Plex username or email to renew',
        duration='Duration of subscription'
    )
    @app_commands.choices(duration=[
        app_commands.Choice(name="1 Month", value="1_month"),
        app_commands.Choice(name="3 Months", value="3_months"),
        app_commands.Choice(name="6 Months", value="6_months"),
        app_commands.Choice(name="12 Months", value="12_months")
    ])
    async def renew(self, interaction: discord.Interaction, user_identifier: str, duration: app_commands.Choice[str]):
        try:
            await interaction.response.defer()
            
            # Get current subscription details
            current_subscription = await db.get_subscription(user_identifier)
            if not current_subscription:
                # If not found by plex username/email, try by discord username
                current_subscription = await db.get_subscription_by_discord(user_identifier)
                if not current_subscription:
                    raise ValueError(f"No active subscription found for {user_identifier}")
            
            # Get current subscription details
            details = current_subscription[0]
            server_name = details['server_name']
            discord_username = details.get('discord_username')  # Preserve Discord username
            plex_username = details['plex_username']  # Get the actual Plex username
            payment_method = details.get('payment_method')  # Preserve payment method
            payment_id = details.get('payment_id')  # Preserve payment ID
            
            # Calculate the current subscription's end date to use as new start date
            current_start_date = datetime.strptime(details['start_date'], '%Y-%m-%d')
            current_end_date = calculate_end_date(current_start_date, details['duration'])
            
            # Use the current end date as the new start date
            start_date = current_end_date.strftime('%Y-%m-%d')
            
            # Remove old subscription
            await db.remove_subscription(plex_username)
            
            # Create new subscription with preserved payment info
            subscription_data = {
                'plex_username': plex_username,
                'server_name': server_name,
                'duration': duration.value,
                'start_date': start_date,
                'payment_method': payment_method,
                'payment_id': payment_id
            }
            
            # Add Discord username if it exists
            if discord_username:
                subscription_data['discord_username'] = discord_username
            
            # Add the new subscription (end_date will be calculated automatically)
            await db.add_subscription(subscription_data)
            
            # Calculate end date for display
            end_date = calculate_end_date(datetime.strptime(start_date, '%Y-%m-%d'), duration.value)
            
            # Create embed for response
            embed = discord.Embed(
                title="🔄 Subscription Renewed",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="👤 User",
                value=plex_username,
                inline=False
            )
            
            if discord_username:
                embed.add_field(
                    name="👥 Discord User",
                    value=discord_username,
                    inline=False
                )
            
            embed.add_field(
                name="🖥️ Server",
                value=server_name,
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Duration",
                value=duration.name,
                inline=True
            )
            
            embed.add_field(
                name="📅 Start Date",
                value=start_date,
                inline=True
            )
            
            embed.add_field(
                name="📅 End Date",
                value=end_date.strftime('%Y-%m-%d'),
                inline=True
            )
            
            # Add payment info if available
            if payment_method and payment_id:
                embed.add_field(
                    name="💳 Payment Info",
                    value=f"Method: {payment_method}\nID: {payment_id}",
                    inline=False
                )
            
            embed.set_footer(text="Use /fetch_subscription to view updated subscription details")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in renew command: {str(e)}", exc_info=True)
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Subscription(bot))