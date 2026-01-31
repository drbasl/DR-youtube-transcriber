FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg ca-certificates && apt-get clean

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --upgrade pip && pip install -e .

ENV PORT=8501
ENV PYTHONPATH=/app/src

CMD ["sh", "-c", "streamlit run src/transcribe_cli/app.py --server.port ${PORT} --server.address 0.0.0.0"]
