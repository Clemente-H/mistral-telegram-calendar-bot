# Mistral Telegram Calendar Bot

Bot de Telegram que utiliza Mistral AI para procesar mensajes y crear eventos en Google Calendar.

## Características

- Detección de intenciones mediante Mistral AI
- Creación de eventos en Google Calendar
- Procesamiento de mensajes de texto
- Procesamiento de imágenes para extraer información de eventos
- Soporte para mensajes de voz (próximamente)

## Requisitos

- Python 3.8+
- Token de Telegram Bot (de @BotFather)
- Clave API de Mistral AI
- Credenciales de Google Calendar API
- (Opcional) Credenciales de Firebase

## Configuración

1. Clona este repositorio:
   ```
   git clone https://github.com/tu-usuario/mistral-telegram-calendar-bot.git
   cd mistral-telegram-calendar-bot
   ```

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Crea un archivo `.env` con la siguiente estructura:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   MISTRAL_API_KEY=your_mistral_api_key_here
   MISTRAL_MODEL=mistral-large-latest
   GOOGLE_CREDENTIALS_FILE=credentials.json
   GOOGLE_TOKEN_FILE=token.json
   FIREBASE_CREDENTIALS_FILE=firebase-credentials.json
   ```

4. Configura las credenciales de Google Calendar:
   - Ve a [Google Cloud Console](https://console.cloud.google.com)
   - Crea un proyecto y habilita la API de Google Calendar
   - Crea credenciales OAuth y descarga el archivo JSON como `credentials.json`

## Ejecución

Para ejecutar el bot localmente:

```
python telegram_bot.py
```

## Uso con Docker

Para construir y ejecutar con Docker:

```
docker build -t mistral-telegram-calendar-bot .
docker run -d --name calendar-bot mistral-telegram-calendar-bot
```

## Despliegue en Google Cloud Run

1. Construye la imagen de Docker:
   ```
   docker build -t gcr.io/your-project-id/mistral-telegram-calendar-bot .
   ```

2. Sube la imagen a Google Container Registry:
   ```
   docker push gcr.io/your-project-id/mistral-telegram-calendar-bot
   ```

3. Despliega en Cloud Run:
   ```
   gcloud run deploy mistral-telegram-calendar-bot \
       --image gcr.io/your-project-id/mistral-telegram-calendar-bot \
       --platform managed \
       --allow-unauthenticated
   ```

4. Configura el webhook de Telegram para que apunte a tu URL de Cloud Run.

## Uso

Una vez que el bot está ejecutándose, puedes interactuar con él a través de Telegram:

1. Inicia una conversación con `/start`
2. Envía mensajes como:
   - "Recuérdame reunión con Juan mañana a las 15:00"
   - "Añade cita médica el viernes a las 10:00 en Hospital Central"
3. Envía imágenes de eventos o carteles y el bot extraerá la información
4. Haz clic en el botón "Añadir a mi Calendario" para agregar el evento

## Estructura del proyecto

- `telegram_bot.py`: Punto de entrada principal, maneja interacciones de Telegram
- `mistral_engine.py`: Procesa mensajes con Mistral AI
- `calendar_events.py`: Gestiona interacciones con Google Calendar
- `prompts.py`: Define los prompts utilizados para Mistral AI
- `config.py`: Configuración centralizada

## Licencia

[MIT](LICENSE)