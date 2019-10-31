from flask_restful import Resource
from flask import request, jsonify
from app.statistics import (
    get_inst_att_needed_posts,
    get_stud_att_needed_posts
)
from app.exception import InvalidUsage


class Top_Post(Resource):

    def get(self, course_id, user):
        try:
            num_posts = int(request.args.get('num_posts'))
        except (ValueError, TypeError) as e:
            return {'message': 'Invalid number of posts specified. '
                               'Please specify the number of posts you would like '
                               'as a GET parameter num_posts'}, 400

        posts = None
        if user == 'instructor':
            posts = get_inst_att_needed_posts(course_id, num_posts)
        elif user == 'student':
            posts = get_stud_att_needed_posts(course_id, num_posts)
        return {'posts': posts}, 202

