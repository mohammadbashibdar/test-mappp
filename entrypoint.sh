#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# initiate virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
echo "Virtual environment activated."

# Install Python dependencies
echo "Installing dependencies..."
# Check if requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found!"
    exit 1
fi
pip install -r requirements.txt

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
