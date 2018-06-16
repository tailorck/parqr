from datetime import datetime, timedelta
from hashlib import md5
import logging

from flask import jsonify, make_response, request
from flask_jsonschema import JsonSchema, ValidationError
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler
import pandas as pd

from app import app
from app.parser import Parser
from app.modeltrain import ModelTrain
from app.models import Course, Event, EventData
from app.constants import COURSE_PARSE_TRAIN_INTERVAL_S
from tasksrq import parse_and_train_models
from exception import InvalidUsage, to_dict
from parqr import Parqr

api_endpoint = '/api/'

parqr = Parqr()
parser = Parser()
model_train = ModelTrain()
jsonschema = JsonSchema(app)

logger = logging.getLogger('app')

redis_host = app.config['REDIS_HOST']
redis_port = app.config['REDIS_PORT']
redis = Redis(host=redis_host, port=redis_port, db=0)
queue = Queue(connection=redis)
scheduler = Scheduler(connection=redis)

logger.info('Ready to serve requests')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'endpoint not found'}), 404)


@app.errorhandler(InvalidUsage)
def on_invalid_usage(error):
    return make_response(jsonify(to_dict(error)), error.status_code)


@app.errorhandler(ValidationError)
def on_validation_error(error):
    return make_response(jsonify(to_dict(error)), 400)


def verify_non_empty_json_request(func):
    def wrapper(*args, **kwargs):
        if request.get_data() == '':
            raise InvalidUsage('No request body provided', 400)
        if not request.json:
            raise InvalidUsage('Request body must be in JSON format', 400)
        return func(*args, **kwargs)
    wrapper.func_name = func.func_name
    return wrapper


@app.route('/')
def index():
    return "Hello, World!"


@app.route(api_endpoint + 'event', methods=['POST'])
@verify_non_empty_json_request
@jsonschema.validate('event')
def register_event():
    millis_since_epoch = request.json['time'] / 1000.0

    event = Event()
    event.event_type = request.json['type']
    event.event_name = request.json['eventName']
    event.time = datetime.fromtimestamp(millis_since_epoch)
    event.user_id = request.json['user_id']
    event.event_data = EventData(**request.json['eventData'])

    event.save()
    logger.info('Recorded {} event from cid {}'
                .format(data['type'], data['cid']))

    return jsonify({'message': 'success'}), 200


@app.route(api_endpoint + 'similar_posts', methods=['POST'])
@verify_non_empty_json_request
@jsonschema.validate('query')
def similar_posts():
    course_id = request.json['course_id']
    if not Course.objects(course_id=course_id):
        logger.error('New un-registered course found: {}'.format(course_id))
        raise InvalidUsage("Course with course id {} not supported at this "
                           "time.".format(course_id), 400)

    query = request.json['query']
    similar_posts = parqr.get_recommendations(course_id, query, 5)
    return jsonify(similar_posts)


# TODO: Add additional attributes (i.e. professor, classes etc.)
@app.route(api_endpoint + 'class', methods=['POST'])
@verify_non_empty_json_request
@jsonschema.validate('class')
def register_class():
    cid = request.json['course_id']
    if not redis.exists(cid):
        logger.info('Registering new course: {}'.format(cid))
        curr_time = datetime.now()
        delayed_time = curr_time + timedelta(minutes=5)

        new_course_job = scheduler.schedule(scheduled_time=datetime.now(),
                                            func=parse_and_train_models,
                                            kwargs={"course_id": cid},
                                            interval=COURSE_PARSE_TRAIN_INTERVAL_S)
        redis.set(cid, new_course_job.id)
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID already exists', 500)


@app.route(api_endpoint + 'class', methods=['DELETE'])
@verify_non_empty_json_request
@jsonschema.validate('class')
def deregister_class():
    cid = request.json['course_id']
    if redis.exists(cid):
        logger.info('Deregistering course: {}'.format(cid))
        job_id_str = redis.get(cid)
        scheduler.cancel(job_id_str)
        redis.delete(cid)
        return jsonify({'course_id': cid}), 200
    else:
        raise InvalidUsage('Course ID does not exists', 500)
