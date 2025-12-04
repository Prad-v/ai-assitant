"""Entry script for cluster inventory service."""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import and run
import uvicorn

# Import the app directly from the server module
# We need to handle the hyphenated directory name
import importlib.util
spec = importlib.util.spec_from_file_location(
    "server",
    os.path.join(os.path.dirname(__file__), "server.py")
)
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

app = server_module.app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

