FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements_flask.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_flask.txt

# Install gunicorn for production Flask deployment
RUN pip install --no-cache-dir gunicorn

# Copy application files
COPY streamlit_app.py flask_app.py db_utils.py config.ini ./
COPY templates/ ./templates/

# Copy startup script
COPY start.sh ./
RUN chmod +x start.sh

# Expose ports
# 8501 for Streamlit
# 5003 for Flask
EXPOSE 8501 5003

# Set environment variables with defaults
ENV DB_HOST=localhost \
    DB_PORT=3306 \
    DB_USER=root \
    DB_PASSWORD="" \
    DB_NAME=lego \
    FLASK_PORT=5003

# Run the startup script
CMD ["./start.sh"]





