# Mistral Telegram Calendar Bot

A powerful Telegram bot that uses Mistral AI to intelligently detect user intent and create calendar events from text messages and images.

![Calendar Bot Logo](https://via.placeholder.com/150?text=Calendar+Bot)

## Features

- **Intent Detection**: Automatically identifies when users want to add calendar events versus other types of requests
- **Text Processing**: Extract event details (title, date, time, location) from natural language messages
- **Image Processing**: Extract event information from images of posters, flyers, or screenshots
- **Google Calendar Integration**: Generates links to add events directly to users' Google Calendars
- **Containerized**: Easy to deploy anywhere Docker is supported

## Architecture

The bot is built with a modular architecture:

- **telegram_bot.py**: Handles Telegram interactions and user messages
- **mistral_engine.py**: Processes messages using Mistral AI to detect intent and extract information
- **calendar_events.py**: Manages calendar event creation and link generation
- **prompts.py**: Contains the prompts for the Mistral AI model
- **utils.py**: Utility functions for data handling and formatting

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

3. Create a `.env` file with your credentials:
  ```bash
  cp .env.example .env
   ```

   Then edit the .env file and fill in your credentials:

   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   MISTRAL_API_KEY=your_mistral_api_key_here
   MISTRAL_MODEL=mistral-large-latest
   GOOGLE_CREDENTIALS_FILE=credentials.json
   GOOGLE_TOKEN_FILE=token.json
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

> **Note:** Initially, this project was intended to run on Google Cloud Run (GCR), but to avoid adding billing information, I chose to use a free alternative instead - in this case, Railway.

### Deploying to Railway

[Railway](https://railway.app/) provides a simple, free way to deploy your bot:

1. Create an account on Railway.app
2. Connect your GitHub repository
3. Configure the environment variables:
   - `TELEGRAM_TOKEN`
   - `MISTRAL_API_KEY`
   - `MISTRAL_MODEL`
4. Railway will automatically build and deploy your Docker container
5. Set up a volume or persistent storage for credentials if needed


### Other Deployment Options

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
   jupyter notebook interactive_testing.ipynb
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

## Project Structure

```
mistral-telegram-calendar-bot/
├── src/
│   ├── calendar_events.py     # Calendar integration
│   ├── config.py              # Configuration handling
│   ├── mistral_engine.py      # Mistral AI processing
│   ├── prompts.py             # Prompts for Mistral AI
│   ├── telegram_bot.py        # Telegram bot functionality
│   └── utils.py               # Utility functions
├── test/
│   ├── interactive_testing.ipynb  # Interactive notebook
│   ├── simple_chatbot_test.py     # Simple test script
│   ├── test_calendar_events.py    # Calendar tests
│   ├── test_mistral_engine.py     # Mistral AI tests
│   └── test_images/              # Sample images for testing
├── .env                       # Environment variables
├── .dockerignore              # Docker ignore file
├── Dockerfile                 # Docker configuration
├── LICENSE                    # License file
├── README.md                  # This documentation
└── requirements.txt           # Python dependencies
```

## Extending the Bot

You can extend the bot's capabilities by:

1. Adding new intent types in `prompts.py` and `mistral_engine.py`
2. Implementing new calendar features in `calendar_events.py`
3. Enhancing image processing in the `extract_from_image` method

## Troubleshooting

### Common Issues

1. **Telegram Connection Issues**:
   - Verify your Telegram token is correct
   - Ensure your bot has the proper permissions

2. **Mistral AI Not Working**:
   - Check your API key
   - Verify the model name is correct

3. **Calendar Link Generation Fails**:
   - Ensure the extracted date/time format is correct
   - Check if all required event fields are present


## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the Telegram API wrapper
- [Mistral AI](https://mistral.ai/) for the powerful language model
- [Google Calendar API](https://developers.google.com/calendar) for calendar integration

---

