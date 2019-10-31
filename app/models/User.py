from app.db import db
from passlib.apps import custom_app_context as pwd_context

class User(db.Document):
    username = db.StringField(max_length=32, required=True)
    password_hash = db.StringField(max_length=128, required=True)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)