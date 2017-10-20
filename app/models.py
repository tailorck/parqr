from app import db


class Followup(db.EmbeddedDocument):
    text = db.StringField(required=True)
    responses = db.ListField(db.StringField())


class Post(db.Document):
    cid = db.StringField(required=True)
    pid = db.IntField(required=True, unique_with='cid')
    subject = db.StringField(required=True)
    body = db.StringField(required=True)
    tags = db.ListField(db.StringField(), requred=True)
    s_answer = db.StringField()
    i_answer = db.StringField()
    followups = db.ListField(db.EmbeddedDocumentField(Followup))

    def pprint(self):
        def _format_long_string(string):
            string = string.encode('ascii', 'ignore')
            string = string.replace('\n', ' ')
            string = ' '.join(string.split(' ')[:6]) + '...'
            return string

        attrs = []
        print '<{}: id={!r}>'.format(type(self).__name__, self.id)
        fields = ['cid', 'pid', 'subject', 'body', 'tags', 's_answer',
                  'i_answer', 'followups']
        for name in fields:
            value = getattr(self, name)
            if isinstance(value, unicode):
                value = _format_long_string(value)
            print '    {} = {}'.format(name, value)


class Course(db.Document):
    cid = db.StringField(required=True, unique=True)
    posts = db.ListField(db.ReferenceField(Post, unique=True))
