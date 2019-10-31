from flask_restful import Resource
from app.models.Event import Event
# from app.models.EventData import EventData
from flask import request, jsonify
from datetime import datetime
from app.extensions import logger, schema
from app.exception import verify_non_empty_json_request
from app.schemas import event

class Events(Resource):

    @verify_non_empty_json_request
    # @schema.validate(event)
    def post(self):
        millis_since_epoch = request.json['time'] / 1000.0
        event = Event()
        event.event_type = request.json['type']
        event.event_name = request.json['eventName']
        event.time = datetime.fromtimestamp(millis_since_epoch)
        event.user_id = request.json['user_id']
        # event.event_data = EventData(**request.json['eventData'])
        event.event_data = request.json['eventData']
        event.course_id = request.json['course_id']

        event.save()
        logger.info('Recorded {} event from cid {}'
                    .format(event.event_name, event.event_data.course_id))

        return {'message': 'success'}, 200

