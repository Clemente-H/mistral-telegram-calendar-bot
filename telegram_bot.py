import os
import logging
import tempfile
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler,
    filters, 
    ContextTypes
)

from config import TELEGRAM_TOKEN
from src.mistral_engine import MistralEngine
from src.audio_processor import AudioProcessor
from src.calendar_events import create_event, generate_calendar_link

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Mistral engine
mistral_engine = MistralEngine()

#Initialize Audio Processor
audio_processor = AudioProcessor()
audio_processor.load_model("tiny")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {user_name}! I'm your calendar assistant. "
        f"You can ask me to add events to your calendar. "
        f"For example: 'Remind me about meeting with John on Friday at 3:00 PM' "
        f"or send me an image of an event."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command."""
    await update.message.reply_text(
        "I can help you manage your calendar. Here are some examples of what you can do:\n\n"
        "- \"Remind me to buy milk tomorrow at 10am\"\n"
        "- \"Add work meeting on Monday at 9:00\"\n"
        "- Send an image of an event poster\n"
        "- Send a voice message describing an event\n\n"
        "To get started, simply type or send a message with the event information."
    )

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes text messages."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Let the user know we're processing
    processing_message = await update.message.reply_text("Processing your message...")
    
    try:
        # Process the message with Mistral
        intent_data, extracted_info, _ = mistral_engine.process_message(message_text)
        
        # Handle based on the intent
        if intent_data.get('intent') == 'add_event':
            await handle_add_event(update, context, extracted_info, processing_message)
        elif intent_data.get('intent') == 'greet':
            await update.message.reply_text("Hello! How can I help you with your calendar today?")
            await processing_message.delete()
        elif intent_data.get('intent') == 'help':
            await help_command(update, context)
            await processing_message.delete()
        else:
            await update.message.reply_text(
                "I'm not sure what you want to do. Can you be more specific? "
                "For example, \"Add meeting with Peter on Friday at 3:00 PM\"."
            )
            await processing_message.delete()
    
    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing your message. Please try again."
        )
        await processing_message.delete()

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes audio messages sent by the user."""
    user_id = update.effective_user.id
    
    # Let the user know we're processing
    processing_message = await update.message.reply_text("Processing your audio message...")
    
    try:
        # Get the audio file
        audio_file = await context.bot.get_file(update.message.voice.file_id)
        
        # Download the audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            await audio_file.download_to_drive(temp_file.name)
            
            # Transcribe audio using Whisper
            transcription = audio_processor.transcribe_audio(temp_file.name)
            
            if transcription:
                # Log transcription result
                logger.info(f"Audio transcription: {transcription}")
                
                # Notify user
                await update.message.reply_text(f"I heard: \"{transcription}\"")
                
                # Process the transcription with Mistral
                intent_data, extracted_info, _ = mistral_engine.process_message(transcription)
                
                # Handle based on the intent
                if intent_data.get('intent') == 'add_event':
                    await handle_add_event(update, context, extracted_info, processing_message)
                elif intent_data.get('intent') == 'greet':
                    await update.message.reply_text("Hello! How can I help you with your calendar today?")
                    await processing_message.delete()
                elif intent_data.get('intent') == 'help':
                    await help_command(update, context)
                    await processing_message.delete()
                else:
                    await update.message.reply_text(
                        "I couldn't identify a calendar event in your message. "
                        "Please try again with more specific details about the event."
                    )
                    await processing_message.delete()
            else:
                await update.message.reply_text(
                    "Sorry, I couldn't transcribe your audio message. "
                    "Please try again or send your message as text."
                )
                await processing_message.delete()
            
        # Delete the temporary file
        os.unlink(temp_file.name)
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing your audio. Please try again."
        )
        await processing_message.delete()

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes images sent by the user."""
    user_id = update.effective_user.id
    
    # Let the user know we're processing
    processing_message = await update.message.reply_text("Processing your image...")
    
    try:
        # Get the image with the highest available resolution
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        
        # Download the image temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            
            # Read the image data
            with open(temp_file.name, 'rb') as f:
                image_data = f.read()
        
        # Delete the temporary file
        os.unlink(temp_file.name)
        
        # Process the image with Mistral
        intent_data, extracted_info, _ = mistral_engine.process_message(image_data, is_image=True)
        
        # Handle based on the intent
        if intent_data.get('intent') == 'add_event':
            await handle_add_event(update, context, extracted_info, processing_message)
        else:
            await update.message.reply_text(
                "I couldn't detect event information in this image. "
                "Please send a clearer image or provide the event details in text."
            )
            await processing_message.delete()
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing your image. Please try again."
        )
        await processing_message.delete()

async def handle_add_event(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: Dict[str, Any], processing_message: Any) -> None:
    """
    Handles the intent to add an event to the calendar.
    
    Args:
        update: Telegram Update object
        context: Conversation context
        event_data: Extracted event data
        processing_message: Processing message to delete
    """
    # Check if there's enough information to create the event
    if not event_data.get('summary') or not event_data.get('start_time'):
        await update.message.reply_text(
            "I need more information about the event. "
            "Please specify at least a title and a date/time."
        )
        await processing_message.delete()
        return
    
    # Generate Calendar link
    calendar_link = generate_calendar_link(event_data)
    
    # Create inline keyboard with the link
    keyboard = [
        [InlineKeyboardButton("Add to my Calendar", url=calendar_link)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Generate response
    event_details = (
        f"📅 *{event_data.get('summary')}*\n"
        f"📆 {event_data.get('start_time')}\n"
    )
    
    if event_data.get('location'):
        event_details += f"📍 {event_data.get('location')}\n"
    
    if event_data.get('description'):
        event_details += f"📝 {event_data.get('description')}\n"
    
    # Respond to the user
    await update.message.reply_text(
        f"I extracted the following event details:\n\n{event_details}\n"
        f"You can add it to your calendar by clicking the button below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await processing_message.delete()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles general errors."""
    logger.error(f"Error: {context.error} - Update: {update}")
    
    try:
        # Inform the user only if we have a chat to respond to
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An unexpected error occurred. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error sending error message: {str(e)}")

def create_application():
    """Creates and configures the application."""
    # Create the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text))
    application.add_handler(MessageHandler(filters.PHOTO, process_image))
    application.add_handler(MessageHandler(filters.VOICE, process_audio))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    return application

def main() -> None:
    """Main function to start the bot."""
    application = create_application()
    
    # Check if we're in production or development
    APP_URL = os.environ.get('APP_URL')
    
    if APP_URL:
        # We're in production (Railway) - use webhook
        PORT = int(os.environ.get('PORT', 8443))
        logger.info(f"Starting webhook on port {PORT} with URL {APP_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{APP_URL}/{TELEGRAM_TOKEN}"
        )
    else:
        # We're in development - use polling
        logger.info("Starting polling (development mode)")
        application.run_polling()

if __name__ == '__main__':
    main()