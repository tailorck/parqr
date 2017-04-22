from flask import Flask
from flask_mongoengine import MongoEngine
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

db = MongoEngine(app)

log_file = os.path.join(app.config['LOG_FOLDER'], 'app.log')
handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
app.logger.addHandler(handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
