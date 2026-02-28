# Use a slim Python image
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies
# ffmpeg is needed for audio/video processing
# build-essential is often needed for compiling python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
# --no-cache-dir reduces image size by not saving the wheels to cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the bot
CMD ["python", "bot.py"]
