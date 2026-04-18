FROM python:3.9-slim

WORKDIR /app

# Install system level dependencies for PDF rendering (pycairo/xhtml2pdf)
RUN apt-get update && apt-get install -y \
    gcc \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies required by python backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the internal port for FastAPI
EXPOSE 8000

# Run FastAPI backend using uvicorn
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
