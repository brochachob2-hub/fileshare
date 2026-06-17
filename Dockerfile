FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir gunicorn -r requirements.txt

RUN useradd -m -u 1000 appuser && mkdir -p /data/uploads && chown -R appuser:appuser /app /data

COPY . .

USER appuser

EXPOSE 8080

ENV UPLOAD_FOLDER=/data/uploads
ENV PORT=8080

CMD gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 app:app
