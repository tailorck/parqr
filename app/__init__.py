import os

from flask_mongoengine import MongoEngine

from utils import create_app


app = create_app(os.environ['FLASK_CONF'])
db = MongoEngine(app)
