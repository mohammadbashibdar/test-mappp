FROM python:latest

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Use entrypoint script
CMD ["./entrypoint.sh"]
