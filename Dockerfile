# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies as root
RUN playwright install-deps

# Hugging Face Spaces requires running as a non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Change working directory to the user's home and copy the app
WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# Install Playwright browsers (Chromium) as user so it installs to the user's home directory
RUN playwright install chromium

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

# Run the FastAPI server on port 7860
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
