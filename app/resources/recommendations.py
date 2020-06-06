from flask_restful import Resource

from app.statistics import (
    get_inst_att_needed_posts,
    get_stud_att_needed_posts
)


class StudentRecommendations(Resource):

    def get(self, course_id):
        posts = get_stud_att_needed_posts(course_id, 5)
        return {'message': 'success', 'recommendations': posts}, 200


class InstructorRecommendations(Resource):

    def get(self, course_id):
        posts = get_inst_att_needed_posts(course_id, 99999)
        return {'message': 'success', 'recommendations': posts}, 200
