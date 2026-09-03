FROM python:3.12-slim

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV DAGSTER_HOME=/opt/dagster/dagster_home/
RUN mkdir -p $DAGSTER_HOME
RUN mkdir -p /opt/dagster/app
RUN mkdir -p /opt/dagster/input_data

WORKDIR /opt/dagster/app

# Install dependencies required for pipeline and DB logic
RUN pip install --no-cache-dir \
    dagster \
    dagster-webserver \
    polars \
    psycopg2-binary \
    SQLAlchemy

EXPOSE 3000

# Start command is overridden in docker-compose.yml
