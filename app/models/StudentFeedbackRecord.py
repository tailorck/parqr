from app.db import db
from app.models.QueryRecommendationPair import QueryRecommendationPair


class StudentFeedbackRecord(db.Document):
    course_id = db.StringField(required=True)
    user_id = db.StringField(required=True)
    time = db.DateTimeField(required=True)
    query_rec_pair = db.ReferenceField(QueryRecommendationPair, required=True)
    feedback_pid = db.IntField(required=True)
    user_rating = db.IntField(required=True)