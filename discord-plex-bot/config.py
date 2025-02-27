# Configuration file for tokens and API keys
import os
from dotenv import load_dotenv

load_dotenv()

# Debug mode
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

# Discord configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Supabase table names
SUBSCRIPTIONS_TABLE = 'subscriptions'
PLEX_SERVERS_TABLE = 'plex_servers'

# API endpoints
SUPABASE_API_URL = f"{SUPABASE_URL}/rest/v1"

# Validate configuration
def validate_config():
    required_vars = [
        ('DISCORD_BOT_TOKEN', DISCORD_BOT_TOKEN),
        ('SUPABASE_URL', SUPABASE_URL),
        ('SUPABASE_KEY', SUPABASE_KEY)
    ]
    
    missing_vars = [var[0] for var in required_vars if not var[1]]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Validate configuration on import
validate_config() 