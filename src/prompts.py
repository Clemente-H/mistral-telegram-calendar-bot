# Prompt to detect user intent
INTENT_DETECTION_PROMPT = """
Analyze the following message and determine the user's intent.
Reply with a JSON containing:
1. "intent": one of the following values:
   - "add_event": if the user wants to add an event to the calendar
   - "greet": if the user is greeting
   - "help": if the user is asking for help
   - "other": for any other intent
2. "confidence": a value between 0 and 1 indicating confidence in the detection
3. "explanation": a brief explanation of why this intent was chosen

User message: {user_message}
"""

# Prompt to extract event information
EVENT_EXTRACTION_PROMPT = """
Extract event information from the following message.
Reply with a JSON containing:
1. "summary": title or summary of the event
2. "location": event location (if mentioned)
3. "description": detailed description of the event
4. "start_time": start time in ISO format (YYYY-MM-DDTHH:MM:SS)
5. "end_time": end time in ISO format (YYYY-MM-DDTHH:MM:SS)
6. "confidence": a value between 0 and 1 indicating confidence in the extraction

If any field is not present in the message, return null for that field.
Take into account that the current date and time are: {current_datetime}.
If only a day of the week is mentioned, assume it's the next occurrence of that day.

User message: {user_message}
"""

# Prompt to extract text and event information from images
IMAGE_EXTRACTION_PROMPT = """
Look at this image and extract any information related to an event.
Focus on identifying:
1. Event title
2. Date and time
3. Location
4. Any other relevant information

Reply with a JSON containing:
1. "extracted_text": the visible text in the image
2. "summary": title or summary of the event
3. "location": event location (if shown)
4. "description": detailed description of the event
5. "start_time": start time in ISO format (YYYY-MM-DDTHH:MM:SS)
6. "end_time": end time in ISO format (YYYY-MM-DDTHH:MM:SS)
7. "confidence": a value between 0 and 1 indicating confidence in the extraction

If any field is not visible in the image, return null for that field.
"""

# Prompt for bot responses
BOT_RESPONSE_PROMPT = """
Generate a natural and friendly response for the user based on the following information:

Detected intent: {intent}
Extracted information: {extracted_info}
Action result: {action_result}

The response should be conversational, brief and in English. If there's a problem or missing information,
you should explain it and ask for the necessary information.
"""