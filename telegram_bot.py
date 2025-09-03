import os
import logging
import tempfile
import secrets
from typing import Dict, Any
from urllib.parse import urljoin
import asyncio
import json

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

def get_google_flow(redirect_uri: str) -> Flow:
    """
    Creates a Google OAuth Flow object, loading credentials from an environment
    variable in production or a local file in development.
    """
    creds_json_str = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json_str:
        # Production: Load from environment variable
        client_config = json.loads(creds_json_str)
        return Flow.from_client_config(
            client_config, scopes=GOOGLE_SCOPES, redirect_uri=redirect_uri
        )
    else:
        # Development: Load from local file
        if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"{GOOGLE_CREDENTIALS_FILE} not found. Please ensure it is in the root directory "
                "or set GOOGLE_CREDENTIALS_JSON environment variable."
            )
        return Flow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=redirect_uri
        )

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
        
        flow = get_google_flow(get_redirect_uri())
        
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
        f"Hello {user_name}! I'm your calendar assistant.\n\n"
        f"To get started, connect your Google Calendar using the /connect command.\n\n"
        f"Then, you can ask me things like 'Remind me about the meeting with John on Friday at 3 PM' "
        f"or send me an image of an event."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "I can help you manage your calendar. Here's what you can do:\n\n"
        "1. Connect your calendar with /connect.\n"
        "2. Send me a text, audio, or image with event information.\n"
        "3. Disconnect your calendar at any time with /disconnect.\n"
        "4. Check the connection status with /status."
    )

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the OAuth2 flow to connect a user's Google Calendar."""
    user_id = str(update.effective_user.id)
    
    if database.get_creds(user_id):
        await update.message.reply_text("Your Google Calendar is already connected. "
                                      "If you want to use a different account, please /disconnect first.")
        return

    flow = get_google_flow(get_redirect_uri())
    
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
        else:
            await update.message.reply_text("I'm not sure what you mean. Please try to be more specific.")
            await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing text: {e}", exc_info=True)
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
            await update.message.reply_text(f'I heard: "{transcription}"')
            intent_data, extracted_info, _ = mistral_engine.process_message(transcription)
            if intent_data.get('intent') == 'add_event':
                await handle_add_event(update, context, extracted_info, processing_message)
            else:
                await update.message.reply_text("I couldn't identify an event in your audio.")
                await processing_message.delete()
        else:
            await update.message.reply_text("I couldn't transcribe your audio.")
            await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
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
            await update.message.reply_text("I couldn't detect an event in the image.")
            await processing_message.delete()
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
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
    """Log the error and send a telegram message to notify the user."""
    logger.error(f"Error: {context.error} - Update: {update}", exc_info=context.error)
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An unexpected error occurred. Please try again later."
        )

# --- Application Setup and Main ---

async def telegram_webhook_handler(request: web.Request) -> web.Response:
    """Handles incoming Telegram updates by parsing them and passing them to the application."""
    application = request.app['bot_app']
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response()
    except json.JSONDecodeError:
        logger.warning("Received invalid JSON in webhook")
        return web.Response(status=400)
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return web.Response(status=500)

def create_application() -> Application:
    """Creates and configures the Telegram bot application."""
    builder = Application.builder().token(TELEGRAM_TOKEN)
    builder.pool_timeout(3600).get_updates_pool_timeout(3600)
    application = builder.build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("connect", connect_command))
    application.add_handler(CommandHandler("disconnect", disconnect_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text))
    application.add_handler(MessageHandler(filters.PHOTO, process_image))
    application.add_handler(MessageHandler(filters.VOICE, process_audio))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    return application

async def main() -> None:
    """Initializes the bot and starts the webserver or polling."""
    application = create_application()
    
    APP_URL = os.environ.get('APP_URL')
    if APP_URL:
        # --- Production Mode (Webhook) ---
        PORT = int(os.environ.get('PORT', 8080))
        
        await application.initialize()
        await application.bot.set_webhook(
            url=f"{APP_URL}/{TELEGRAM_TOKEN}",
            allowed_updates=Update.ALL_TYPES
        )
        
        # Create the aiohttp web application
        web_app = web.Application()
        web_app['bot_app'] = application
        
        # Add handlers for the bot webhook and the OAuth callback
        web_app.router.add_post(f"/{TELEGRAM_TOKEN}", telegram_webhook_handler)
        web_app.router.add_get('/oauth2callback', oauth_callback)
        
        # Start the web server
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
        await site.start()
        
        logger.info(f"Web server started on port {PORT}")
        
        await application.start()
        
        # Keep the script running
        while True:
            await asyncio.sleep(3600)
            
    else:
        # --- Development Mode (Polling) ---
        logger.info("Starting bot in polling mode.")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())