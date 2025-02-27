# Supabase connection and table creation logic
import logging
from datetime import datetime
from supabase import create_client, Client
import httpx
from config import (
    SUPABASE_URL, 
    SUPABASE_KEY, 
    SUBSCRIPTIONS_TABLE, 
    PLEX_SERVERS_TABLE,
    SUPABASE_API_URL
)
from utils.date_utils import calculate_end_date

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }

    async def execute_raw_query(self, query: str):
        """Execute a raw SQL query using Supabase REST API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_API_URL}/rest/v1/rpc/execute_sql",
                    headers=self.headers,
                    json={"sql": query}
                )
                response.raise_for_status()
                logger.debug(f"SQL query executed successfully: {query[:100]}...")
                return response.json()
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
            raise

    # Subscription Methods
    async def add_subscription(self, subscription_data):
        """Add a new subscription"""
        try:
            # Calculate end date based on start date and duration
            start_date = datetime.strptime(subscription_data['start_date'], '%Y-%m-%d')
            end_date = calculate_end_date(start_date, subscription_data['duration'])
            subscription_data['end_date'] = end_date.strftime('%Y-%m-%d')

            result = self.supabase.table(SUBSCRIPTIONS_TABLE).insert(subscription_data).execute()
            logger.info(f"Added new subscription for user: {subscription_data.get('plex_username')}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error adding subscription: {str(e)}", exc_info=True)
            raise
    
    async def get_subscription(self, plex_username):
        """Get subscription details for a user"""
        try:
            result = self.supabase.table(SUBSCRIPTIONS_TABLE)\
                .select("*")\
                .eq("plex_username", plex_username)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching subscription: {str(e)}", exc_info=True)
            raise
    async def get_all_subscriptions(self):
        """Get all subscriptions"""
        try:
            result = self.supabase.table(SUBSCRIPTIONS_TABLE)\
                .select("*")\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching all subscriptions: {str(e)}", exc_info=True)
            raise
    async def get_plex_server(self, server_name):
        """Get Plex server details"""
        try:
            result = self.supabase.table(PLEX_SERVERS_TABLE)\
                .select("*")\
                .eq("server_name", server_name)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching Plex server: {str(e)}", exc_info=True)
            raise

    async def get_all_plex_servers(self):
        """Get all Plex server details"""
        try:
            result = self.supabase.table(PLEX_SERVERS_TABLE)\
                .select("*")\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching all Plex servers: {str(e)}", exc_info=True)
            raise

    async def get_subscription_by_discord(self, discord_username):
        """Get subscription details by Discord username"""
        try:
            result = self.supabase.table(SUBSCRIPTIONS_TABLE)\
                .select("*")\
                .eq("discord_username", discord_username)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching subscription by Discord username: {str(e)}", exc_info=True)
            raise

    async def remove_subscription(self, plex_username):
        """Remove a subscription for a user"""
        try:
            result = self.supabase.table(SUBSCRIPTIONS_TABLE)\
                .delete()\
                .eq("plex_username", plex_username)\
                .execute()
            logger.info(f"Removed subscription for user: {plex_username}")
            return result.data
        except Exception as e:
            logger.error(f"Error removing subscription: {str(e)}", exc_info=True)
            raise

# Create a singleton instance
db = Database()