from app.db import db


class Followup(db.EmbeddedDocument):
    # text and response are cols in the table
    text = db.StringField(required=True)
    responses = db.ListField(db.StringField())
