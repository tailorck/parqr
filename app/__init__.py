from flask import Flask
from flask_mongoengine import MongoEngine
import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter
import os

formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s '
                              '%(module)-10s: %(message)s')
app = Flask(__name__)

if 'APP_SETTINGS' in os.environ:
    app.config.from_object(os.environ['APP_SETTINGS'])
    log_file = os.path.join(app.config['LOG_FOLDER'], 'app.log')
    log_level = app.config['LOG_LEVEL']
    fh = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
    app.logger.addHandler(fh)
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
    app.logger.setLevel(log_level)
else:
    app.logger.warn('APP_SETTINGS not set. Using default config')
    app.config.from_object('app.config.Config')

db = MongoEngine(app)
