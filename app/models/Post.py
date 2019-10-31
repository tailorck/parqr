from app.db import db
# from app.models import db

from app.models.Followup import Followup


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
        print('<{}: id={!r}>'.format(type(self).__name__, self.id))
        fields = ['course_id', 'post_id', 'subject', 'body', 'tags',
                  's_answer', 'i_answer', 'followups']
        for name in fields:
            value = getattr(self, name)
            if isinstance(value, str):
                value = _format_long_string(value)
            print('    {} = {}'.format(name, value))