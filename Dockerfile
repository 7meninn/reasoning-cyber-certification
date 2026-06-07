FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/app/src
ENV HOSTED_AGENT_API_HOST=0.0.0.0
ENV HOSTED_AGENT_API_PORT=8000

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["python", "-m", "cybersecurity_readiness.hosted_api"]
