# Mistral Telegram Calendar Bot

A Telegram bot that uses Mistral AI to intelligently detect user intent and create calendar events from text messages and images.

## Features

- **Intent Detection**: Automatically identifies when users want to add calendar events versus other types of requests
- **Text Processing**: Extract event details (title, date, time, location) from natural language messages
- **Image Processing**: Extract event information from images of posters, flyers, or screenshots
- **Google Calendar Integration**: Generates links to add events directly to users' Google Calendars
- **Containerized**: Easy to deploy anywhere Docker is supported

## Demo
The bot is currently deployed on Railway. You can test it by searching for [@mistralcalendarassistant_bot] on Telegram

## Architecture

The bot follows a modular architecture for better maintainability and extensibility:

- ```telegram_bot.py ```: Handles Telegram interactions and user messages
- ```mistral_engine.py ```: Processes messages using Mistral AI to detect intent and extract information

-  ```calendar_events.py ```: Manages calendar event creation and link generation
-  ```audio_processor.py ```: Transcribes voice messages using Whisper.cpp
-  ```prompts.py ```: Contains structured prompts for the Mistral AI model
utils.py: Utility functions for data handling and formatting

## Prerequisites

- Python 3.8+
- Docker (for containerized deployment)
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Mistral AI API Key
- Google Cloud credentials (for Calendar integration)

## Installation

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mistral-telegram-calendar-bot.git
   cd mistral-telegram-calendar-bot
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Important:** Obtain the Google Calendar API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (or select an existing one)
   - Enable the Google Calendar API
   - Create OAuth 2.0 Client credentials
   - Download the JSON file and rename it to `credentials.json`
   - Place it in the project root directory

4. Create a `.env` file with your credentials:
  ```bash
  cp .env.example .env
   ```

   Then edit the .env file and fill in your credentials:

   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   MISTRAL_API_KEY=your_mistral_api_key_here
   MISTRAL_MODEL=mistral-large-latest
   GOOGLE_CREDENTIALS_FILE=credentials.json
   ```

5. Run the bot
  ```bash
  python telegram_bot.py
   ```

### Docker Setup

1. Build the Docker image:
   ```bash
   docker build -t calendar-bot .
   ```

2. Run the container:
   ```bash
   docker run -d --name calendar-bot \
     -e TELEGRAM_TOKEN=your_telegram_bot_token \
     -e MISTRAL_API_KEY=your_mistral_api_key \
     -e MISTRAL_MODEL=mistral-large-latest \
     -v /path/to/credentials.json:/app/credentials.json \
     calendar-bot
   ```

## Deployment

The bot is designed to be easily deployable to various cloud platforms. It automatically detects whether it's running in a local environment or production.
Currenntly is deployed on [Railway](https://railway.app/) on the free tier.

### Local Development

For local development, simply run the bot without setting the `APP_URL` environment variable:

```bash
python telegram_bot.py
```

The bot will automatically use polling mode when running locally.

### Switching Between Environments

The bot automatically detects which environment it's running in:

- **With APP_URL**: Uses webhook mode (suitable for production)
- **Without APP_URL**: Uses polling mode (suitable for development)

This ensures you can develop locally with the same codebase that you deploy to production.


### Alternative Deployment Options

The bot can also be deployed to:
- Google Cloud Run
- AWS ECS
- Heroku
- Render
- Fly.io

## Testing

The project includes comprehensive testing tools:

1. An interactive Jupyter notebook for exploring functionality:
   ```bash
   cd test
   jupyter notebook testing_and_debugging.ipynb
   ```

2. A simple console-based test script:
   ```bash
   python test/simple_chatbot_test.py
   ```

## Usage

Once the bot is running:

1. Start a conversation with your bot on Telegram
2. Use `/start` to get an introduction
3. Send messages like:
   - "Remind me about the meeting with John tomorrow at 3pm"
   - "Add dentist appointment next Tuesday at 2:30pm at Central Dental Clinic"
4. Send images of event posters or flyers
5. Click the "Add to Calendar" button to add events to your Google Calendar

## Intent Detection Examples

The bot can detect different user intents:

- **Add Event**: "Schedule a team meeting for Friday at 10am"
- **Greeting**: "Hello! How are you today?"
- **Help Request**: "What can you do for me?"
- **Other**: (any other type of message)

## Image Processing

The bot uses Mistral AI's image understanding capabilities to extract information from images:
- Event posters
- Flyers
- Screenshots of event details
- Digital invitations

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the Telegram API wrapper
- [Mistral AI](https://mistral.ai/) for the powerful language model
- [Google Calendar API](https://developers.google.com/calendar) for calendar integration

---

