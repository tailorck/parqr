from app import app
from flask_mongoengine import MongoEngine

db = MongoEngine(app)
