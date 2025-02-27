# Functions to manage Plex user invitations and removals
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
import logging

logger = logging.getLogger(__name__)

def get_all_users_from_server(plex_url, plex_token):
    try:
        # Connect to Plex server
        plex_url = plex_url.strip()
        account = MyPlexAccount(token=plex_token)
        plex = PlexServer(plex_url, plex_token)
        
        # Get all users
        users = account.users()
        
        # Format user data with library access information
        user_list = []
        for user in users:
            # Check if user has any libraries shared with them
            has_library_access = False
            try:
                # Get user's shared libraries
                shared_servers = user.servers
                for server in shared_servers:
                    if server.name == plex.friendlyName:
                        has_library_access = True
                        break
            except Exception as e:
                logger.warning(f"Could not check library access for {user.username}: {str(e)}")
                
            user_list.append({
                'username': user.username,
                'email': user.email,
                'library_access': has_library_access
            })
        
        logger.info(f"Successfully retrieved {len(user_list)} users from Plex server")
        return user_list
    except Exception as e:
        logger.error(f"Error getting users from Plex: {str(e)}", exc_info=True)
        raise

def get_user_details(plex_token, identifier):
    """
    Get both username and email for a user when either one is provided.
    The identifier can be either a username or an email.
    Returns a tuple of (username, email) if found, or (identifier, None) if not found.
    """
    try:
        # Connect to account using token
        account = MyPlexAccount(token=plex_token)
        
        # Get all users
        users = account.users()
        
        # Check if identifier is an email (contains @)
        is_email = '@' in identifier
        
        # Search for the user
        for user in users:
            if is_email and user.email and user.email.lower() == identifier.lower():
                return (user.username, user.email)
            elif not is_email and user.username.lower() == identifier.lower():
                return (user.username, user.email)
                
        # If we reach here, user wasn't found
        logger.warning(f"User with identifier {identifier} not found in Plex users list")
        return (identifier, None)
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}", exc_info=True)
        return (identifier, None)

def invite_user_to_plex(plex_url, plex_token, identifier):
    try:
        # Connect to Plex server - strip any whitespace from URL
        plex_url = plex_url.strip()
        plex = PlexServer(plex_url, plex_token)
        # Get account associated with the token
        account = MyPlexAccount(token=plex_token)
        
        # Get complete user details (username and email)
        username, email = get_user_details(plex_token, identifier)
        
        # Check if user is already invited/exists
        existing_users = [user.username.lower() for user in account.users()]
        if username.lower() in existing_users:
            logger.warning(f"User {username} is already a member of the Plex server")
            # Return user details even if already invited
            return {'invited': False, 'username': username, 'email': email}
            
        # Send invitation
        account.inviteFriend(
            user=identifier,  # Use original identifier for invitation
            server=plex,
            sections=plex.library.sections(),  # Share all libraries
            allowSync=True,
            allowCameraUpload=False,
            allowChannels=True
        )
        logger.info(f"Successfully invited user {username} to Plex server")
        return {'invited': True, 'username': username, 'email': email}
    except Exception as e:
        logger.error(f"Error inviting user to Plex: {str(e)}", exc_info=True)
        raise

def remove_user_from_plex(plex_url, plex_token, identifier):
    try:
        # Connect directly to account using token
        account = MyPlexAccount(token=plex_token)
        
        # Clean the URL by removing any whitespace
        plex_url = plex_url.strip()
        plex = PlexServer(plex_url, plex_token)
        
        # Get complete user details (username and email)
        username, email = get_user_details(plex_token, identifier)
        
        # Get list of users
        users = account.users()
        # Case-insensitive username comparison
        user_to_remove = next((user for user in users if user.username.lower() == username.lower()), None)
        
        if user_to_remove:
            # Remove user from server
            account.removeFriend(user_to_remove.username)
            logger.info(f"Successfully removed user {username} from Plex server")
            return True
        else:
            logger.warning(f"User {identifier} not found on Plex server")
            return False
    except Exception as e:
        logger.error(f"Error removing user from Plex: {str(e)}", exc_info=True)
        raise