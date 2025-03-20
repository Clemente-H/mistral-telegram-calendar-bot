import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mistral_engine import MistralEngine
from src.calendar_events import generate_calendar_link
sys.path.append('../../')
from config import MISTRAL_API_KEY

def test_chat_flow():
    """
    Simple test to simulate a chat flow with the bot.
    This is a basic console test that processes user messages and shows responses.
    """
    if not MISTRAL_API_KEY:
        print("Error: MISTRAL_API_KEY not found in environment variables.")
        return
    
    engine = MistralEngine()
    
    # Sample user messages to test
    user_messages = [
        "Hello! How are you?",
        "Can you add a meeting with John tomorrow at 2pm?",
        "Schedule a dentist appointment next Monday at 10am at Smile Dental Clinic"
    ]
    
    print("=== Starting Chat Flow Test ===")
    for msg in user_messages:
        print(f"\nUser: {msg}")
        
        # Process the message
        intent_data, extracted_info, _ = engine.process_message(msg)
        
        print(f"Detected intent: {intent_data.get('intent')} (confidence: {intent_data.get('confidence', 0):.2f})")
        
        # Handle based on intent
        if intent_data.get('intent') == 'add_event':
            if extracted_info.get('summary') and extracted_info.get('start_time'):
                # Format the event details
                event_details = []
                event_details.append(f"📅 {extracted_info.get('summary')}")
                event_details.append(f"📆 {extracted_info.get('start_time')}")
                
                if extracted_info.get('location'):
                    event_details.append(f"📍 {extracted_info.get('location')}")
                
                if extracted_info.get('description'):
                    event_details.append(f"📝 {extracted_info.get('description')}")
                
                # Generate calendar link
                calendar_link = generate_calendar_link(extracted_info)
                
                print("Bot: I extracted the following event details:")
                print("\n".join(event_details))
                print(f"\nAdd to calendar: {calendar_link}")
            else:
                print("Bot: I need more information about the event.")
        elif intent_data.get('intent') == 'greet':
            print("Bot: Hello! How can I help you with your calendar today?")
        else:
            print("Bot: I'm not sure what you want to do. Can you be more specific?")
        
        print("-" * 50)
    
    print("\n=== Chat Flow Test Complete ===")

def test_image_processing(image_path):
    """
    Test image processing with a sample event image.
    
    Args:
        image_path: Path to an image file to test
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    if not MISTRAL_API_KEY:
        print("Error: MISTRAL_API_KEY not found in environment variables.")
        return
    
    engine = MistralEngine()
    
    print("=== Starting Image Processing Test ===")
    
    # Read the image file
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Process the image
    intent_data, extracted_info, _ = engine.process_message(image_data, is_image=True)
    
    print(f"Detected intent: {intent_data.get('intent')} (confidence: {intent_data.get('confidence', 0):.2f})")
    print("\nExtracted information:")
    print(json.dumps(extracted_info, indent=2))
    
    # If it's an event, generate a calendar link
    if intent_data.get('intent') == 'add_event' and extracted_info.get('summary') and extracted_info.get('start_time'):
        calendar_link = generate_calendar_link(extracted_info)
        print(f"\nAdd to calendar: {calendar_link}")
    
    print("\n=== Image Processing Test Complete ===")

if __name__ == "__main__":
    # Run the chat flow test
    test_chat_flow()
    
    # Test image processing if an image path is provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_image_processing(image_path)
    else:
        print("\nTo test image processing, run this script with an image path:")
        print("python test/simple_chatbot_test.py path/to/event_image.jpg")