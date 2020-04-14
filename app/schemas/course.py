from app.extensions import ma


class CoursesListSchema(ma.Schema):
    active = ma.fields.Boolean(required=False, default=False)
