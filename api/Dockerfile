# FastAPI + Uvicorn Dockerfile
FROM python:3.10-slim

# Install curl, netcat-openbsd, and postgresql-client for healthchecks, wait-for-db, and schema init
RUN apt-get update \
	&& apt-get install -y curl netcat-openbsd postgresql-client \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .


# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
