import json
import base64
import logging
import datetime
from typing import Dict, Any, Optional, Union, Tuple

# Actualización: usar la biblioteca más reciente
from mistralai import Mistral 
from PIL import Image
import io

from config import MISTRAL_API_KEY, MISTRAL_MODEL
from src.prompts import (
    INTENT_DETECTION_PROMPT, 
    EVENT_EXTRACTION_PROMPT, 
    IMAGE_EXTRACTION_PROMPT,
    BOT_RESPONSE_PROMPT
)

# Configure logging
logger = logging.getLogger(__name__)

class MistralEngine:
    def __init__(self):
        """Initializes the processing engine with Mistral AI."""
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        self.model = MISTRAL_MODEL
    
    def _call_mistral(self, prompt: str) -> str:
        """
        Makes a call to the Mistral API.
        
        Args:
            prompt: The prompt to send to Mistral
            
        Returns:
            str: The response from Mistral
        """
        try:
            # Formato actualizado para mensajes
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Mistral: {str(e)}")
            return ""
        
    def _call_mistral_with_image(self, prompt: str, image_data: bytes) -> str:
        """
        Makes a call to the Mistral API with an image.
        
        Args:
            prompt: The prompt to send to Mistral
            image_data: Binary data of the image
            
        Returns:
            str: The response from Mistral
        """
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Create the message structure according to Mistral's documentation
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]
            
            # Call the API with the formatted message
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Mistral with image: {str(e)}")
            return ""
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Extracts and parses the JSON response from Mistral.
        
        Args:
            response: Text response from Mistral
            
        Returns:
            Dict: Parsed JSON content or empty dictionary if there's an error
        """
        try:
            # Try to find JSON in the response
            json_str = ""
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                # Look for JSON patterns
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx+1]
            
            # Parse JSON
            if json_str:
                return json.loads(json_str)
            return {}
        except Exception as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return {}
    
    def detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Detects the user's intent from a message.
        
        Args:
            message: User message
            
        Returns:
            Dict: Information about the detected intent
        """
        prompt = INTENT_DETECTION_PROMPT.format(user_message=message)
        response = self._call_mistral(prompt)
        intent_data = self._parse_json_response(response)
        
        # Set default values if information is missing
        if not intent_data or 'intent' not in intent_data:
            intent_data = {
                'intent': 'other',
                'confidence': 0.0,
                'explanation': 'Could not detect intent'
            }
        
        return intent_data
    
    def extract_event_info(self, message: str) -> Dict[str, Any]:
        """
        Extracts event information from a message.
        
        Args:
            message: User message
            
        Returns:
            Dict: Extracted event information
        """
        current_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = EVENT_EXTRACTION_PROMPT.format(
            user_message=message,
            current_datetime=current_dt
        )
        
        response = self._call_mistral(prompt)
        event_data = self._parse_json_response(response)
        
        # Ensure all fields are present
        if not event_data:
            event_data = {}
        
        # Check and complete missing fields
        for field in ['summary', 'location', 'description', 'start_time', 'end_time', 'confidence']:
            if field not in event_data:
                event_data[field] = None
        
        return event_data
    
    def extract_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extracts event information from an image.
        
        Args:
            image_data: Binary data of the image
            
        Returns:
            Dict: Extracted event information
        """
        prompt = IMAGE_EXTRACTION_PROMPT
        response = self._call_mistral_with_image(prompt, image_data)
        event_data = self._parse_json_response(response)
        
        # Ensure all fields are present
        if not event_data:
            event_data = {}
        
        # Check and complete missing fields
        for field in ['extracted_text', 'summary', 'location', 'description', 
                     'start_time', 'end_time', 'confidence']:
            if field not in event_data:
                event_data[field] = None
        
        return event_data
    
    def generate_response(self, intent: str, extracted_info: Dict, action_result: Dict) -> str:
        """
        Generates a response for the user.
        
        Args:
            intent: Detected intent
            extracted_info: Information extracted from the message
            action_result: Result of the performed action
            
        Returns:
            str: Generated response
        """
        prompt = BOT_RESPONSE_PROMPT.format(
            intent=intent,
            extracted_info=json.dumps(extracted_info, ensure_ascii=False),
            action_result=json.dumps(action_result, ensure_ascii=False)
        )
        
        response = self._call_mistral(prompt)
        
        # Remove possible code markers
        if '```' in response:
            response = response.replace('```', '').strip()
        
        return response
    
    def process_message(self, message: Union[str, bytes], is_image: bool = False) -> Tuple[Dict, Dict, Dict]:
        """
        Processes a user message, detects intent and extracts information.
        
        Args:
            message: User message (text or image data)
            is_image: True if the message is an image
            
        Returns:
            Tuple: (intent, extracted information, result)
        """
        # If it's an image, extract information directly
        if is_image:
            extracted_info = self.extract_from_image(message)
            
            # Determine intent based on extraction confidence
            confidence = extracted_info.get('confidence', 0)
            # Ensure confidence is a number, not None
            if confidence is None:
                confidence = 0
            intent_data = {
                'intent': 'add_event' if confidence >= 0.5 else 'other',
                'confidence': confidence,
                'explanation': 'Information extracted from image'
            }
            
            return intent_data, extracted_info, {}
        
        # If it's text, process normally
        message_text = message if isinstance(message, str) else message.decode('utf-8')
        intent_data = self.detect_intent(message_text)
        
        # If the intent is to add an event, extract information
        if intent_data.get('intent') == 'add_event':
            extracted_info = self.extract_event_info(message_text)
        else:
            extracted_info = {}
        
        return intent_data, extracted_info, {}