from app import db
import pdb


class Post(db.Document):
    cid = db.StringField(required=True)
    pid = db.IntField(required=True, unique_with='cid')
    subject = db.StringField(required=True)
    body = db.StringField(required=True)
    tags = db.ListField(db.StringField(), requred=True)
    s_answer = db.StringField()
    i_answer = db.StringField()

    def __str__(self):
        return '<{}: id={!r}>'.format(type(self).__name__, self.id)

    def __repr__(self):
        def _format_long_string(string):
            string = string.encode('ascii', 'ignore')
            string = string.replace('\n', ' ')
            string = ' '.join(string.split(' ')[:6]) + '...'

        attrs = []
        for name in self._fields.keys():
            value = getattr(self, name)
            if isinstance(value, unicode):
                value = _format_long_string(value)
            attrs.append('\n    {} = {},'.format(name, value))
        return '<{}: {}\n>'.format(type(self).__name__, ''.join(attrs))


class Course(db.Document):
    cid = db.StringField(required=True, unique=True)
    posts = db.ListField(db.ReferenceField(Post, unique=True))
