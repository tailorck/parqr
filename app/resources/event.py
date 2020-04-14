import copy
import uuid

import boto3
from flask_restful import (
    Resource,
    request
)


class Event(Resource):

    def __init__(self):
        dynamodb_resource = boto3.resource('dynamodb')
        self.events = dynamodb_resource.Table('Events')

    def post(self):
        event_type = request.json.get("event_type")
        user_id = request.json.get("user_id")
        course_id = request.json.get("course_id")
        event_data = request.json.get("event_data")

        print("Event {} happened with user_id {} in course_id {} with event_data {}".format(
            event_type, user_id, course_id, event_data
        ))

        event = copy.deepcopy(request.json)
        event['uuid'] = str(uuid.uuid4())
        self.events.put_item(
            Item=event
        )

        return {'message': 'success'}, 200
