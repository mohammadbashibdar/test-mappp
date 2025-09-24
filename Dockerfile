FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose FastAPI port
EXPOSE 8000

# Entrypoint
CMD ["./entrypoint.sh"]



# FROM python:latest

# WORKDIR /app

# # Copy requirements first for better caching
# COPY requirements.txt .

# # Install dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the application code
# COPY . .

# # Make entrypoint script executable
# RUN chmod +x entrypoint.sh

# # Expose port
# EXPOSE 8000

# # Use entrypoint script
# CMD ["./entrypoint.sh"]
