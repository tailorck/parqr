from app.db import db
from app.models.Post import Post


class QueryRecommendationPair(db.Document):
    course_id = db.StringField(required=True)
    time = db.DateTimeField(required=True)
    query = db.StringField(required=True)
    recommended_pids = db.ListField(db.IntField())