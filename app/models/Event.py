from app.db import db
# from app.models.EventData import EventData


class Event(db.Document):
    event_type = db.StringField(required=True)
    event_name = db.StringField(required=True)
    time = db.DateTimeField(required=True)
    user_id = db.StringField(required=True)
    # event_data = db.EmbeddedDocumentField(EventData, default=EventData,
    #                                       required=True)

    event_data = db.DictField(required=True)
    course_id = db.StringField(required=True)
