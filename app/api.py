import logging
import json
import pdb

from flask import jsonify, make_response, request
from flask_jsonschema import JsonSchema, ValidationError
import pandas as pd

from app import app
from app.modeltrain import ModelTrain
from app.models import Course
from exception import InvalidUsage, to_dict
from parqr import Parqr
from scraper import Scraper

api_endpoint = '/api/'

parqr = Parqr()
scraper = Scraper()
model_train = ModelTrain()
jsonschema = JsonSchema(app)

logger = logging.getLogger('app')


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
    data = {}
    data['cid'] = request.json['eventData']['cid']
    data['type'] = request.json['eventName']
    data['uid'] = request.json['uid']
    data['time'] = request.json['time']

    df = pd.DataFrame(data, index=[0])

    with open('events.csv', 'a') as outfile:
        df.to_csv(outfile, header=False, index=False)

    return jsonify({'msg': 'success'}), 200


@app.route(api_endpoint + 'train_all_models', methods=['POST'])
@verify_non_empty_json_request
def train_all_models():
    model_train.persist_all_models()
    return jsonify({'msg': 'training all models'}), 202


@app.route(api_endpoint + 'train_model', methods=['POST'])
@verify_non_empty_json_request
def train_model():
    if 'course_id' not in request.json:
        raise InvalidUsage('Course ID not found in JSON', 400)

    cid = request.json['course_id']
    model_train.persist_model(cid)

    return jsonify({'course_id': cid}), 202


@app.route(api_endpoint + 'course', methods=['POST'])
@verify_non_empty_json_request
def update_course():
    if 'course_id' not in request.json:
        raise InvalidUsage('Course ID not found in JSON', 400)

    course_id = request.json['course_id']
    scraper.update_posts(course_id)
    return jsonify({'course_id': course_id}), 202


@app.route(api_endpoint + 'similar_posts', methods=['POST'])
@verify_non_empty_json_request
@jsonschema.validate('query')
def similar_posts():
    course_id = request.json['cid']
    if not Course.objects(cid=course_id):
        logger.error('New un-registered course found: {}'.format(course_id))
        raise InvalidUsage("Course with cid {} not supported at this "
                           "time.".format(course_id), 400)

    query = request.json['query']
    similar_posts = parqr.get_recommendations(course_id, query, 5)
    return jsonify(similar_posts)
