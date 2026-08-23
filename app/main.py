import uvicorn
from app.config.web_config import web_config
from app.logr.logr import setup_logging

if __name__ == '__main__':
    setup_logging()
    uvicorn.run(app="app.api.app:app", host=web_config.host, port=web_config.port)