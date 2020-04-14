from marshmallow import Schema, fields


class RecommendationSchema(Schema):
    num_posts = fields.Int(required=False, default=5)
