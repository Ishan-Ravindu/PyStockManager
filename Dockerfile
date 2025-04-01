FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Django and other dependencies directly
COPY pyproject.toml .
RUN pip install django>=5.1.7,\<6.0.0 django-jazzmin>=3.0.1,\<4.0.0 gunicorn psycopg2-binary

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run gunicorn
CMD ["gunicorn", "mssports.wsgi:application", "--bind", "0.0.0.0:8000"]