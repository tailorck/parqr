from app.db import db
from app.models.query_recommendation_pair import QueryRecommendationPair


class StudentFeedbackRecord(db.Document):
    feedback_pid = db.IntField(required=True)

    time = db.DateTimeField(required=True)
    query_rec_pair = db.ReferenceField(QueryRecommendationPair, required=True)
    user_rating = db.IntField(required=True)

    user_id = db.StringField(required=True)
    course_id = db.StringField(required=True)
    event_data = db.DictField()
