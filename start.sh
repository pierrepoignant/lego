#!/bin/bash

# Start script for running both Streamlit and Flask apps

echo "Starting Flask app on port ${FLASK_PORT}..."
gunicorn --bind 0.0.0.0:${FLASK_PORT} --workers 2 flask_app:app &

echo "Starting Streamlit app on port 8501..."
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true &

# Wait for both processes
wait -n

# Exit with status of process that exited first
exit $?
