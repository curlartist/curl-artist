import os
from waitress import serve
from app import app  # Imports your Flask app object

# Configuration
HOST = '0.0.0.0'  # 0.0.0.0 allows access from other devices (like your phone)
PORT = 8000       # The port the site will run on
THREADS = 4       # How many requests to handle at once

if __name__ == "__main__":
    print(f" -> Starting Waitress server on http://localhost:{PORT}")
    print(f" -> Serving on all network interfaces (access via IP: {PORT})")
    print(f" -> Press Ctrl+C to stop")
    
    # Run the server
    serve(app, host=HOST, port=PORT, threads=THREADS)