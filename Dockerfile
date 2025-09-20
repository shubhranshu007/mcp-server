# Use lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app


# Install system dependencies (for git, gcc if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for Flask/MCP
EXPOSE 8000

# Run MCP server
CMD ["python", "main.py"]
