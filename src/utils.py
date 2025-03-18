import os
import base64
import logging
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import tempfile
import uuid

# Configure logging
logger = logging.getLogger(__name__)

def format_datetime_for_user(dt_str: str) -> str:
    """
    Formats an ISO datetime to present it to the user.
    
    Args:
        dt_str: Datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
        
    Returns:
        str: Datetime formatted for the user
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        # Format: "Monday, 18 of March at 15:30"
        return dt.strftime("%A, %d of %B at %H:%M").capitalize()
    except:
        return dt_str

def parse_user_datetime(date_text: str, relative_to: Optional[datetime] = None) -> Optional[str]:
    """
    Converts datetime text to ISO format.
    This is a placeholder function - ideally we would use Mistral for this.
    
    Args:
        date_text: Datetime text (e.g. "tomorrow at 3pm")
        relative_to: Reference datetime (default: now)
        
    Returns:
        Optional[str]: Datetime in ISO format or None if it couldn't be parsed
    """
    # This function should be implemented with a language model
    # or a specific library for parsing natural language dates
    # For now we return None to indicate that it couldn't be parsed
    return None

def generate_unique_filename(prefix: str = "", suffix: str = "") -> str:
    """
    Generates a unique filename.
    
    Args:
        prefix: Prefix for the filename
        suffix: Suffix for the filename
        
    Returns:
        str: Unique filename
    """
    return f"{prefix}{uuid.uuid4()}{suffix}"

def create_temp_file(data: bytes, suffix: str = "") -> str:
    """
    Creates a temporary file with the provided data.
    
    Args:
        data: Binary data to write to the file
        suffix: Suffix for the filename
        
    Returns:
        str: Path to the temporary file
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(data)
            return temp_file.name
    except Exception as e:
        logger.error(f"Error creating temporary file: {str(e)}")
        return ""

def safe_delete_file(file_path: str) -> bool:
    """
    Safely deletes a file.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False

def format_event_for_display(event_data: Dict[str, Any]) -> str:
    """
    Formats event data to display to the user.
    
    Args:
        event_data: Event data
        
    Returns:
        str: Formatted text to display to the user
    """
    result = []
    
    # Event title
    summary = event_data.get('summary', 'Untitled event')
    result.append(f"📅 *{summary}*")
    
    # Date and time
    if event_data.get('start_time'):
        start_time = format_datetime_for_user(event_data['start_time'])
        result.append(f"📆 {start_time}")
    
    # Location
    if event_data.get('location'):
        result.append(f"📍 {event_data['location']}")
    
    # Description
    if event_data.get('description'):
        description = event_data['description']
        # Truncate very long descriptions
        if len(description) > 200:
            description = description[:197] + "..."
        result.append(f"📝 {description}")
    
    return "\n".join(result)