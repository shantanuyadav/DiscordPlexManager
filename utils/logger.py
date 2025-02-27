# Logging setup for database operations
import logging
import os

# Configure logging to write to a file
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set logging level for database module to ERROR
db_logger = logging.getLogger('database')
db_logger.setLevel(logging.ERROR)
