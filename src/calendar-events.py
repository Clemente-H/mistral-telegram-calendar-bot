import os
import json
import datetime
import logging
from typing import Dict, Optional, Tuple, Any

import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE, GOOGLE_SCOPES

# Configure logging
logger = logging.getLogger(__name__)

def get_calendar_service(token_path: Optional[str] = None) -> Tuple[Any, bool]:
    """
    Gets a Google Calendar service.
    
    Args:
        token_path: Path to the token file. If None, will use the default.
        
    Returns:
        Tuple[Any, bool]: The Calendar service and whether bot credentials were used (True) or not (False)
    """
    creds = None
    token_file = token_path or GOOGLE_TOKEN_FILE
    
    # Check if a valid token exists
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as token:
                creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                    json.load(token), GOOGLE_SCOPES)
        except Exception as e:
            logger.error(f"Error loading token: {str(e)}")
    
    # If there are no valid credentials, use the bot's
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error refreshing token: {str(e)}")
                creds = None
                
        # If user credentials couldn't be obtained, use the bot's
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error obtaining credentials: {str(e)}")
                return None, False
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service, True
    except HttpError as error:
        logger.error(f"Error building service: {str(error)}")
        return None, False

def create_event(event_data: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates an event in Google Calendar.
    
    Args:
        event_data: Dictionary with event data
        user_token: User token (optional)
        
    Returns:
        Dict: Result of the operation
    """
    # Get Calendar service
    service, using_bot_credentials = get_calendar_service(user_token)
    
    if not service:
        return {
            "success": False,
            "message": "Could not connect to Google Calendar",
            "event_link": None
        }
    
    # Prepare event for Google Calendar
    event = {
        'summary': event_data.get('summary', 'Untitled event'),
        'location': event_data.get('location', ''),
        'description': event_data.get('description', ''),
        'start': {
            'dateTime': event_data.get('start_time'),
            'timeZone': 'America/Santiago',  # Adjust as needed
        },
        'end': {
            'dateTime': event_data.get('end_time'),
            'timeZone': 'America/Santiago',  # Adjust as needed
        },
        'reminders': {
            'useDefault': True,
        },
    }
    
    # If there's no end time, set it 1 hour after the start
    if not event_data.get('end_time') and event_data.get('start_time'):
        start_dt = datetime.datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00'))
        end_dt = start_dt + datetime.timedelta(hours=1)
        event['end']['dateTime'] = end_dt.isoformat()
    
    try:
        # Use the primary calendar
        calendar_id = 'primary'
        
        # Create the event
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        # Get link to add to calendar
        event_link = event.get('htmlLink', '')
        
        return {
            "success": True,
            "message": "Event created successfully",
            "event_id": event.get('id'),
            "event_link": event_link,
            "using_bot_credentials": using_bot_credentials
        }
        
    except HttpError as error:
        logger.error(f"Error creating event: {str(error)}")
        return {
            "success": False,
            "message": f"Error creating event: {str(error)}",
            "event_link": None
        }

def generate_calendar_link(event_data: Dict[str, Any]) -> str:
    """
    Generates a link to add an event to Google Calendar without needing the API.
    
    Args:
        event_data: Dictionary with event data
        
    Returns:
        str: URL to add the event to Google Calendar
    """
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    
    # Prepare parameters
    params = {
        "text": event_data.get('summary', 'Untitled event'),
        "details": event_data.get('description', ''),
        "location": event_data.get('location', ''),
    }
    
    # Add dates if available
    if event_data.get('start_time'):
        start_dt = datetime.datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00'))
        params["dates"] = start_dt.strftime("%Y%m%dT%H%M%S")
        
        # If there's an end time
        if event_data.get('end_time'):
            end_dt = datetime.datetime.fromisoformat(event_data['end_time'].replace('Z', '+00:00'))
            params["dates"] += "/" + end_dt.strftime("%Y%m%dT%H%M%S")
        else:
            # If there's no end time, set it 1 hour after the start
            end_dt = start_dt + datetime.timedelta(hours=1)
            params["dates"] += "/" + end_dt.strftime("%Y%m%dT%H%M%S")
    
    # Build URL
    url_params = "&".join([f"{k}={v}" for k, v in params.items() if v])
    return f"{base_url}&{url_params}"