import datetime
import logging
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src import database

logger = logging.getLogger(__name__)

def create_event_with_creds(creds: Credentials, event_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Creates an event in Google Calendar using provided user credentials.
    It also handles token refresh and saves the new token if necessary.

    Args:
        creds: Google OAuth2 credentials object for the user.
        event_data: Dictionary with event details extracted by Mistral.
        user_id: The user's ID to save refreshed tokens.

    Returns:
        A dictionary with the result of the operation.
    """
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info(f"Credentials for user {user_id} have expired. Refreshing...")
            try:
                creds.refresh(Request())
                database.save_creds(user_id, creds)
                logger.info(f"Successfully refreshed and saved credentials for user {user_id}")
            except Exception as e:
                logger.error(f"Error refreshing credentials for user {user_id}: {e}")
                return {"success": False, "message": "Your authorization has expired. Please use /disconnect and /connect again."}
        else:
            return {"success": False, "message": "Your credentials are not valid. Please connect your calendar."}

    try:
        service = build('calendar', 'v3', credentials=creds)
        
        event = {
            'summary': event_data.get('summary', 'Untitled Event'),
            'location': event_data.get('location', ''),
            'description': event_data.get('description', ''),
            'start': {
                'dateTime': event_data.get('start_time'),
                'timeZone': 'America/Santiago',  # This could be made user-configurable
            },
            'end': {
                'dateTime': event_data.get('end_time'),
                'timeZone': 'America/Santiago',
            },
            'reminders': {'useDefault': True},
        }

        if not event_data.get('end_time') and event_data.get('start_time'):
            start_dt = datetime.datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00'))
            end_dt = start_dt + datetime.timedelta(hours=1)
            event['end']['dateTime'] = end_dt.isoformat()

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        return {
            "success": True,
            "message": "Event created successfully.",
            "event_id": created_event.get('id'),
            "event_link": created_event.get('htmlLink')
        }

    except HttpError as error:
        logger.error(f"An error occurred for user {user_id}: {error}")
        return {"success": False, "message": f"Failed to create event: {error}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred for user {user_id}: {e}")
        return {"success": False, "message": "An unexpected error occurred."}