import os

from flask import jsonify, make_response
from flask_cors import CORS
from flask_restful import Api, request, abort
from app.resources.course import (
    CoursesList,
    ActiveCourse,
    FindCourseByCourseID
)
from app.resources.event import Event
from app.resources.query import InstructorQuery
from app.resources.recommendations import StudentRecommendations, InstructorRecommendations
from app.resources.user import Users
from app.resources.feedback import Feedbacks
from app.utils import create_app
from app.exception import InvalidUsage, to_dict
import awsgi


class CustomApi(Api):

    def handle_error(self, e):
        abort(e.code, str(e))


api_endpoint = '/{}/'.format(os.environ.get('stage'))
app = create_app("")
CORS(app)
api = CustomApi(app)

api.add_resource(CoursesList, api_endpoint + 'courses')
api.add_resource(FindCourseByCourseID, api_endpoint + 'courses/<string:course_id>')
api.add_resource(ActiveCourse, api_endpoint + 'courses/<string:course_id>/active')

# Replaced by direct call to parqr_lambda
# api.add_resource(StudentQuery, api_endpoint + 'courses/<string:course_id>/query/student')
# api.add_resource(InstructorQuery, api_endpoint + 'courses/<string:course_id>/query/instructor')

api.add_resource(StudentRecommendations, api_endpoint + 'courses/<string:course_id>/recommendation/student')
api.add_resource(InstructorRecommendations, api_endpoint + 'courses/<string:course_id>/recommendation/instructor')

api.add_resource(Event, api_endpoint + 'event')
api.add_resource(Feedbacks, api_endpoint + 'feedback')

api.add_resource(Users, api_endpoint + 'users')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'endpoint not found'}), 404)


@app.errorhandler(InvalidUsage)
def on_invalid_usage(error):
    return make_response(jsonify(to_dict(error)), error.status_code)


@app.route(api_endpoint, methods=['GET', 'POST'])
def index():
    return "Hello, World!"


def lambda_handler(event, context):
    print(os.environ.get('stage'), event, context)
    response = awsgi.response(app, event, context)
    print(response)
    return response
