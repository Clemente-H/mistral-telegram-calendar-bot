import os
import logging
import tempfile
import secrets
from typing import Dict, Any
from urllib.parse import urljoin

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from aiohttp import web
from google_auth_oauthlib.flow import Flow

from config import TELEGRAM_TOKEN, GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES
from src.mistral_engine import MistralEngine
from src.audio_processor import AudioProcessor
from src.calendar_events import create_event_with_creds
from src import database

# --- Basic Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- App Initialization ---
mistral_engine = MistralEngine()
audio_processor = AudioProcessor()
audio_processor.load_model("tiny")

# This dictionary will temporarily store the state for the OAuth flow
# In a larger application, you might use a database or Redis for this
oauth_states: Dict[str, str] = {}

# --- OAuth & Web Server Functions ---

def get_redirect_uri() -> str:
    """Constructs the redirect URI from environment variables."""
    app_url = os.environ.get('APP_URL')
    if not app_url:
        logger.warning("APP_URL environment variable not set. Using localhost.")
        return "http://localhost:8080/oauth2callback"
    return urljoin(app_url, '/oauth2callback')

async def oauth_callback(request: web.Request) -> web.Response:
    """
    Handles the redirect from Google after user authorization.
    This is part of the web server, not the Telegram bot logic.
    """
    try:
        params = request.query
        state = params.get('state')
        
        if not state or state not in oauth_states:
            logger.warning("Received OAuth callback with invalid state.")
            return web.Response(text="Error: Invalid state parameter. Please try connecting again.", status=400)

        user_id = oauth_states.pop(state)
        
        flow = Flow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=GOOGLE_SCOPES,
            redirect_uri=get_redirect_uri()
        )
        
        flow.fetch_token(authorization_response=str(request.url))
        creds = flow.credentials
        
        database.save_creds(user_id, creds)
        
        logger.info(f"Successfully saved credentials for user {user_id}")
        
        # Notify the user back in Telegram
        application = request.app['bot_app']
        await application.bot.send_message(
            chat_id=user_id,
            text="✅ Great! Your Google Calendar has been successfully connected. I can now add events directly."
        )
        
        return web.Response(text="Authorization complete! You can now close this window and return to Telegram.")
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        return web.Response(text="An error occurred during the authorization process. Please try again.", status=500)

# --- Telegram Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {user_name}! I\'m your calendar assistant.\n\n"
        f"To get started, connect your Google Calendar using the /connect command.\n\n"
        f"Then, you can ask me things like 'Remind me about the meeting with John on Friday at 3 PM' "
        f"or send me an image of an event."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "I can help you manage your calendar. Here\'s what you can do:\n\n"
        "1. Connect your calendar with /connect.\n"
        "2. Send me a text, audio, or image with event information.\n"
        "3. Disconnect your calendar at any time with /disconnect.\n"
        "4. Check the connection status with /status."
    )

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the OAuth2 flow to connect a user\'s Google Calendar."""
    user_id = str(update.effective_user.id)
    
    if database.get_creds(user_id):
        await update.message.reply_text("Your Google Calendar is already connected. "
                                      "If you want to use a different account, please /disconnect first.")
        return

    flow = Flow.from_client_secrets_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=get_redirect_uri()
    )
    
    flow.access_type = 'offline'
    flow.prompt = 'consent'
    
    state = secrets.token_urlsafe(16)
    oauth_states[state] = user_id
    
    authorization_url, _ = flow.authorization_url(state=state)
    
    keyboard = [[InlineKeyboardButton("Connect to Google Calendar", url=authorization_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "To add events directly to your calendar, I need your permission. "
        "Please click the button below to authorize access to your Google Calendar.",
        reply_markup=reply_markup
    )

async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disconnects the user\'s Google Calendar."""
    user_id = str(update.effective_user.id)
    if database.get_creds(user_id):
        database.delete_token(user_id)
        await update.message.reply_text("Your calendar has been disconnected. I have deleted your credentials from my system.")
    else:
        await update.message.reply_text("You didn\'t have a calendar connected.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks if the user\'s calendar is connected."""
    user_id = str(update.effective_user.id)
    if database.get_creds(user_id):
        await update.message.reply_text("✅ Your Google Calendar is connected.")
    else:
        await update.message.reply_text("❌ Your Google Calendar is not connected. Use /connect to get started.")

# --- Core Processing Functions ---

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    processing_message = await update.message.reply_text("Processing your message...")
    try:
        intent_data, extracted_info, _ = mistral_engine.process_message(message_text)
        
        if intent_data.get('intent') == 'add_event':
            await handle_add_event(update, context, extracted_info, processing_message)
        # ... (other intents)
        else:
            await update.message.reply_text("I\'m not sure what you mean. Please try to be more specific.")
        await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        await processing_message.delete()
        await update.message.reply_text("Sorry, an error occurred while processing your message.")

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    processing_message = await update.message.reply_text("Processing your audio...")
    try:
        audio_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            await audio_file.download_to_drive(temp_file.name)
            transcription = audio_processor.transcribe_audio(temp_file.name)
        os.unlink(temp_file.name)

        if transcription:
            await update.message.reply_text(f"I heard: \"{transcription}\""
            intent_data, extracted_info, _ = mistral_engine.process_message(transcription)
            if intent_data.get('intent') == 'add_event':
                await handle_add_event(update, context, extracted_info, processing_message)
            else:
                await update.message.reply_text("I couldn\'t identify an event in your audio.")
        else:
            await update.message.reply_text("I couldn\'t transcribe your audio.")
        await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        await processing_message.delete()
        await update.message.reply_text("Sorry, an error occurred while processing your audio.")

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    processing_message = await update.message.reply_text("Processing your image...")
    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            with open(temp_file.name, 'rb') as f:
                image_data = f.read()
        os.unlink(temp_file.name)

        intent_data, extracted_info, _ = mistral_engine.process_message(image_data, is_image=True)
        if intent_data.get('intent') == 'add_event':
            await handle_add_event(update, context, extracted_info, processing_message)
        else:
            await update.message.reply_text("I couldn\'t detect an event in the image.")
        await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await processing_message.delete()
        await update.message.reply_text("Sorry, an error occurred while processing your image.")

async def handle_add_event(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: Dict[str, Any], processing_message: Any) -> None:
    user_id = str(update.effective_user.id)
    
    if not event_data.get('summary') or not event_data.get('start_time'):
        await update.message.reply_text("I need more information. Please specify at least a title and a date/time.")
        await processing_message.delete()
        return

    creds = database.get_creds(user_id)
    if not creds:
        await update.message.reply_text(
            "Your calendar is not connected. Please use the /connect command to authorize me."
        )
        await processing_message.delete()
        return

    await processing_message.edit_text("Creating event in your Google Calendar...")

    try:
        result = create_event_with_creds(creds, event_data, user_id)
        if result and result.get("success"):
            event_details = (
                f"📅 *{event_data.get('summary')}*\n"
                f"📆 {event_data.get('start_time')}\n"
            )
            keyboard = [[InlineKeyboardButton("View Event in Google Calendar", url=result.get('event_link'))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Event created successfully!\n\n{event_details}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"Could not create the event. Error: {result.get('message')}")
    except Exception as e:
        logger.error(f"Failed to create event for user {user_id}: {e}")
        await update.message.reply_text("An unexpected error occurred while creating the event in your calendar.")
    
    await processing_message.delete()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error} - Update: {update}")
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An unexpected error occurred. Please try again."
        )

# --- Application Setup and Main ---

def create_application() -> Application:
    builder = Application.builder().token(TELEGRAM_TOKEN)
    builder.pool_timeout(3600).get_updates_pool_timeout(3600)
    application = builder.build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("connect", connect_command))
    application.add_handler(CommandHandler("disconnect", disconnect_command))
    application.add_handler(CommandHandler("status", status_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text))
    application.add_handler(MessageHandler(filters.PHOTO, process_image))
    application.add_handler(MessageHandler(filters.VOICE, process_audio))
    
    application.add_error_handler(error_handler)
    
    return application

def main() -> None:
    application = create_application()
    
    APP_URL = os.environ.get('APP_URL')
    if APP_URL:
        PORT = int(os.environ.get('PORT', 8080))
        
        web_app = web.Application()
        web_app.add_routes([web.get('/oauth2callback', oauth_callback)])
        web_app['bot_app'] = application
        
        logger.info(f"Starting webhook and web server on port {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{APP_URL}/{TELEGRAM_TOKEN}",
            web_app=web_app
        )
    else:
        logger.info("Starting polling (development mode)")
        logger.warning("OAuth callback will not work in polling mode without a tunnel like ngrok.")
        application.run_polling()

if __name__ == '__main__':
    main()