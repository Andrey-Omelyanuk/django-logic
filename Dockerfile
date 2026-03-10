FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project and install
COPY . .
RUN pip install --no-cache-dir -e . coverage

# Disable bytecode compilation
ENV PYTHONDONTWRITEBYTECODE=1
# Unbuffer stdout and stderr
ENV PYTHONUNBUFFERED=1
# Set default command
CMD ["python", "tests/manage.py", "runserver", "0.0.0.0:8000"]

