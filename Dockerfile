FROM python:3.11-slim

WORKDIR /app

# Copiar los archivos de requisitos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos
COPY . .

# Variable de entorno para indicar que estamos en producción
ENV ENVIRONMENT production

# Ejecutar el bot cuando se inicie el contenedor
CMD ["python", "telegram_bot.py"]