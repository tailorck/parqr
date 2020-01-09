from flask import jsonify, make_response
from flask_restful import Api, request, abort
from flask_jwt import JWTError
from app.resources.course import (
    CoursesList,
    ActiveCourse,
)

from app.resources.event import Event
from app.resources.query import StudentQuery, InstructorQuery
from app.resources.recommendations import StudentRecommendations, InstructorRecommendations
from app.resources.user import Users
from app.resources.feedback import Feedback
from app.exception import InvalidUsage, to_dict
from app import app


class CustomApi(Api):

    def handle_error(self, e):
        abort(e.code, str(e))


api_endpoint = '/api/v2.0'
api = CustomApi(app)

api.add_resource(CoursesList, api_endpoint + '/courses')
api.add_resource(ActiveCourse, api_endpoint + '/course/<string:course_id>/active')

api.add_resource(StudentQuery, api_endpoint + '/course/<string:course_id>/query/student')
api.add_resource(InstructorQuery, api_endpoint + '/course/<string:course_id>/query/instructor')

api.add_resource(StudentRecommendations, api_endpoint + '/course/<string:course_id>/recommendation/student')
api.add_resource(InstructorRecommendations, api_endpoint + '/course/<string:course_id>/recommendation/instructor')


api.add_resource(Event, api_endpoint + '/event')
api.add_resource(Feedback, api_endpoint + '/feedback')

api.add_resource(Users, api_endpoint + '/users')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'endpoint not found'}), 404)


@app.errorhandler(InvalidUsage)
def on_invalid_usage(error):
    return make_response(jsonify(to_dict(error)), error.status_code)


@app.route('/')
def index():
    return "Hello, World!"
