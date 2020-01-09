from flask_restful import Resource
from flask import request
from app.extensions import feedback
from app.feedback import Feedback
from app.utils import verify_non_empty_json_request


class Feedback(Resource):

    @verify_non_empty_json_request
    def post(self):
        # Validate the feedback data
        course_id, user_id, query_rec_id, feedback_pid, user_rating = Feedback.unpack_feedback(request.json)
        valid, message = feedback.validate_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating)

        # If not failed, return invalid usage
        if not valid:
            return {'message': "Feedback contains invalid data. " + message}, 400
        success = Feedback.register_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating)

        if success:
            return {'message': 'success'}, 200

        else:
            return {'message': 'failure'}, 500
