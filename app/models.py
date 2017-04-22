from app import db


class Post(db.Document):
    cid = db.StringField(required=True)
    pid = db.IntField(required=True, unique_with='cid')
    subject = db.StringField(required=True)
    body = db.StringField(required=True)
    tags = db.ListField(db.StringField(), requred=True)


class Course(db.Document):
    cid = db.StringField(required=True, unique=True)
    posts = db.ListField(db.ReferenceField(Post, unique=True))
