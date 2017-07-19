from flask import Flask
from flask_mongoengine import MongoEngine
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)

if 'APP_SETTINGS' in os.environ:
    app.config.from_object(os.environ['APP_SETTINGS'])
    log_file = os.path.join(app.config['LOG_FOLDER'], 'app.log')
    handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
    app.logger.addHandler(handler)
    app.logger.setLevel(app.config['LOG_LEVEL'])
else:
    app.logger.warn('APP_SETTINGS not set. Using default config')
    app.config.from_object('app.config.Config')

db = MongoEngine(app)
