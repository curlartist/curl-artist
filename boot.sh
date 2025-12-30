#!/bin/bash

# This script activates Gunicorn with 4 workers
# It binds to 0.0.0.0 so the internet can see it

echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8000 app:app