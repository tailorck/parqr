from flask import Flask
from flask_mongoengine import MongoEngine
import logging

app = Flask(__name__)
app.config.from_object('app.config.Config')

db = MongoEngine(app)

handler = logging.StreamHandler()
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)
