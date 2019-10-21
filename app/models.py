from app import app
from flask_mongoengine import MongoEngine
from passlib.apps import custom_app_context as pwd_context

db = MongoEngine(app)


class Followup(db.EmbeddedDocument):
    text = db.StringField(required=True)
    responses = db.ListField(db.StringField())


class Post(db.Document):
    course_id = db.StringField(required=True)
    created = db.DateTimeField(required=True)
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

    def pprint(self):
        def _format_long_string(string):
            string = string.encode('ascii', 'ignore')
            string = string.replace('\n', ' ')
            string = ' '.join(string.split(' ')[:6]) + '...'
            return string

        attrs = []
        print '<{}: id={!r}>'.format(type(self).__name__, self.id)
        fields = ['course_id', 'post_id', 'subject', 'body', 'tags',
                  's_answer', 'i_answer', 'followups']
        for name in fields:
            value = getattr(self, name)
            if isinstance(value, unicode):
                value = _format_long_string(value)
            print '    {} = {}'.format(name, value)


class Course(db.Document):
    course_id = db.StringField(required=True, unique=True)
    course_name = db.StringField(required=True)
    course_number = db.StringField(required=True)
    course_term = db.StringField(required=True)
    posts = db.ListField(db.ReferenceField(Post, unique=True))


class EventData(db.EmbeddedDocument):
    course_id = db.StringField(required=True)
    post_id = db.IntField()
    other_data = db.DictField()

class Event(db.Document):
    event_type = db.StringField(required=True)
    event_name = db.StringField(required=True)
    time = db.DateTimeField(required=True)
    user_id = db.StringField(required=True)
    event_data = db.EmbeddedDocumentField(EventData, default=EventData,
                                          required=True)


class User(db.Document):
    username = db.StringField(max_length=32, required=True)
    password_hash = db.StringField(max_length=128, required=True)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)
