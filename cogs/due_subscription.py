# Checks and notifies about upcoming due subscriptions
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database.db import db
from datetime import datetime, timedelta
from utils.date_utils import calculate_end_date

logger = logging.getLogger(__name__)

def chunk_embed_field(field_name, field_value, inline=False):
    """
    Splits a long embed field value into multiple chunks to avoid Discord's 1024 character limit.
    Returns a list of (name, value, inline) tuples ready to be added to an embed.
    """
    if len(field_value) <= 1024:
        return [(field_name, field_value, inline)]
    
    chunks = []
    lines = field_value.split('\n')
    current_chunk = ""
    chunk_count = 1
    
    for line in lines:
        # If adding this line would exceed the limit, start a new chunk
        if len(current_chunk) + len(line) + 1 > 1024:  # +1 for newline
            if current_chunk:  # Don't add empty chunks
                chunks.append((f"{field_name} (Part {chunk_count})", current_chunk, inline))
                chunk_count += 1
                current_chunk = line
            else:  # Line itself is too long, need to split it
                part = line[:1020] + "..."
                chunks.append((f"{field_name} (Part {chunk_count})", part, inline))
                chunk_count += 1
                current_chunk = "..." + line[1020:]
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
    
    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append((f"{field_name} {f'(Part {chunk_count})' if chunk_count > 1 else ''}".strip(), current_chunk, inline))
    
    return chunks

class DueSubscription(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name='due_subscription',
        description='Check subscriptions due within the next 7 days'
    )
    async def due_subscription(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            # Get all active subscriptions
            subscriptions = await db.get_all_subscriptions()
            if not subscriptions:
                await interaction.followup.send("No active subscriptions found.")
                return

            # Current date for comparison
            current_date = datetime.now()
            due_subscriptions = []

            # Check each subscription
            for sub in subscriptions:
                # Try both date formats - first try DD-MM-YYYY, then YYYY-MM-DD
                try:
                    # Try DD-MM-YYYY format first
                    start_date = datetime.strptime(sub['start_date'], '%d-%m-%Y')
                except ValueError:
                    # If that fails, try YYYY-MM-DD format
                    start_date = datetime.strptime(sub['start_date'], '%Y-%m-%d')
                    
                end_date = calculate_end_date(start_date, sub['duration'])
                days_remaining = (end_date - current_date).days

                if 0 <= days_remaining <= 30:
                    due_subscriptions.append({
                        'username': sub['plex_username'],
                        'server': sub['server_name'],
                        'days_remaining': days_remaining,
                        'end_date': end_date.strftime('%d-%m-%Y')
                    })

            if not due_subscriptions:
                await interaction.followup.send("No subscriptions are due within the next 30 days.")
                return

            # Sort by days remaining
            due_subscriptions.sort(key=lambda x: x['days_remaining'])

            # Group subscriptions by urgency
            critical = [sub for sub in due_subscriptions if sub['days_remaining'] <= 2]
            warning = [sub for sub in due_subscriptions if 2 < sub['days_remaining'] <= 7]
            notice = [sub for sub in due_subscriptions if sub['days_remaining'] > 7]
            
            # Create and send embeds
            await self.send_subscription_embeds(interaction, critical, warning, notice)

        except Exception as e:
            logger.error(f"Error in due_subscription command: {str(e)}", exc_info=True)
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
            
    async def send_subscription_embeds(self, interaction, critical, warning, notice):
        """Create and send embeds for subscription data, handling Discord's limits."""
        # Discord has a limit of 25 fields per embed and 6000 characters total size
        MAX_FIELDS_PER_EMBED = 24  # Using 24 to leave room for a potential info field
        MAX_EMBED_SIZE = 5800  # Setting slightly below 6000 to be safe
        
        # Create the first embed
        embed = discord.Embed(
            title="📊 Subscription Status Overview",
            description="Here are the subscriptions that require attention in the next 30 days.",
            color=discord.Color.blue()
        )
        
        # Track total fields added and estimated embed size
        fields_added = 0
        current_embed_size = len(embed.title) + len(embed.description)
        embeds = [embed]
        
        def get_field_size(name, value):
            # Calculate approximate size of a field
            return len(name) + len(value)
        
        # Process critical subscriptions
        if critical:
            critical_text = "\n".join([f"🔴 **{sub['username']}**\n└ Server: {sub['server']}\n└ Expires: {sub['end_date']} ({sub['days_remaining']} days)" 
                                for sub in critical])
            
            critical_chunks = chunk_embed_field("⚠️ CRITICAL - Action Required (0-2 days)", critical_text, False)
            
            # Add fields to current embed or create new embeds as needed
            for name, value, inline in critical_chunks:
                # Calculate size this field would add
                field_size = get_field_size(name, value)
                
                # If current embed is full or would exceed size limit, create a new one
                if fields_added >= MAX_FIELDS_PER_EMBED or (current_embed_size + field_size) > MAX_EMBED_SIZE:
                    embed = discord.Embed(
                        title="📊 Subscription Status Overview (Continued)",
                        color=discord.Color.blue()
                    )
                    embeds.append(embed)
                    fields_added = 0
                    current_embed_size = len(embed.title)
                
                embed.add_field(name=name, value=value, inline=inline)
                fields_added += 1
                current_embed_size += field_size
        
        # Process warning subscriptions
        if warning:
            warning_text = "\n".join([f"🟡 **{sub['username']}**\n└ Server: {sub['server']}\n└ Expires: {sub['end_date']} ({sub['days_remaining']} days)" 
                                for sub in warning])
            
            warning_chunks = chunk_embed_field("⚠️ WARNING - Expiring Soon (3-7 days)", warning_text, False)
            
            for name, value, inline in warning_chunks:
                # Calculate size this field would add
                field_size = get_field_size(name, value)
                
                # If current embed is full or would exceed size limit, create a new one
                if fields_added >= MAX_FIELDS_PER_EMBED or (current_embed_size + field_size) > MAX_EMBED_SIZE:
                    embed = discord.Embed(
                        title="📊 Subscription Status Overview (Continued)",
                        color=discord.Color.blue()
                    )
                    embeds.append(embed)
                    fields_added = 0
                    current_embed_size = len(embed.title)
                
                embed.add_field(name=name, value=value, inline=inline)
                fields_added += 1
                current_embed_size += field_size
        
        # Process notice subscriptions
        if notice:
            notice_text = "\n".join([f"🟢 **{sub['username']}**\n└ Server: {sub['server']}\n└ Expires: {sub['end_date']} ({sub['days_remaining']} days)" 
                                for sub in notice])
            
            notice_chunks = chunk_embed_field("ℹ️ NOTICE - Upcoming Renewals (8-30 days)", notice_text, False)
            
            for name, value, inline in notice_chunks:
                # Calculate size this field would add
                field_size = get_field_size(name, value)
                
                # If current embed is full or would exceed size limit, create a new one
                if fields_added >= MAX_FIELDS_PER_EMBED or (current_embed_size + field_size) > MAX_EMBED_SIZE:
                    embed = discord.Embed(
                        title="📊 Subscription Status Overview (Continued)",
                        color=discord.Color.blue()
                    )
                    embeds.append(embed)
                    fields_added = 0
                    current_embed_size = len(embed.title)
                
                embed.add_field(name=name, value=value, inline=inline)
                fields_added += 1
                current_embed_size += field_size
        
        # Add footer to the last embed
        embeds[-1].set_footer(text="Use /fetch_subscription <username> for detailed subscription information")
        
        # Send all embeds
        for i, embed in enumerate(embeds):
            if i == 0:
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DueSubscription(bot))