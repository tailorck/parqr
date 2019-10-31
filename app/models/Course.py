from app.db import db
from app.models.Post import Post


class Course(db.Document):
    course_id = db.StringField(required=True, unique=True)
    course_name = db.StringField(required=True)
    course_number = db.StringField(required=True)
    course_term = db.StringField(required=True)
