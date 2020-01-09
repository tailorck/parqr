from flask import request
from flask_restful import Resource
from marshmallow.exceptions import ValidationError

from app.schemas.recommendations import RecommendationSchema
from app.statistics import (
    get_inst_att_needed_posts,
    get_stud_att_needed_posts
)


class StudentRecommendations(Resource):

    def get(self, course_id):
        schema = RecommendationSchema()

        try:
            num_posts = schema.load(request.args)
        except ValidationError as exp:
            return {'message': 'Input validation failed', 'errors': exp.messages}, 400

        posts = get_stud_att_needed_posts(course_id, num_posts)
        return {'message': 'success', 'recommendations': posts}, 200


class InstructorRecommendations(Resource):

    def get(self, course_id):
        schema = RecommendationSchema()

        try:
            num_posts = schema.load(request.args)
        except ValidationError as exp:
            return {'message': 'Input validation failed', 'errors': exp.messages}, 400

        posts = get_inst_att_needed_posts(course_id, num_posts)
        return {'message': 'success', 'recommendations': posts}, 200
