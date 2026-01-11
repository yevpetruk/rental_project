# Dockerfile
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем не-root пользователя для безопасности
RUN useradd -m -u 1000 webuser
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем директории для статики и медиа
RUN mkdir -p /app/static /app/media
RUN chown -R webuser:webuser /app
RUN chmod -R 755 /app

# Переключаемся на не-root пользователя
USER webuser

# Порт для Django
EXPOSE 8000

# Команда запуска
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "rental_project.wsgi:application"]