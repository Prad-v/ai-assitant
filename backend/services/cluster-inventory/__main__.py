"""Entry point for cluster inventory service."""

import uvicorn
from .server import app, HOST, PORT

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)

