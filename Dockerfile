FROM python:3.10

RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Сообщаем Back4App, что мы используем порт
EXPOSE 8080

CMD ["python", "bot.py"]
