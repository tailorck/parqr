from app.db import db
# from app.models import db

from app.models.followup import Followup


class Post(db.Document):
    course_id = db.StringField(required=True)
    created = db.DateTimeField(required=True)
    modified = db.DateTimeField(required=True)
    post_id = db.IntField(required=True, unique_with='course_id')
    subject = db.StringField(required=True)
    body = db.StringField(required=True)
    tags = db.ListField(db.StringField())
    post_type = db.StringField()
    s_answer = db.StringField()
    i_answer = db.StringField()
    followups = db.ListField(db.EmbeddedDocumentField(Followup))
    num_views = db.IntField(required=True)
    num_unresolved_followups = db.IntField(required=True)
