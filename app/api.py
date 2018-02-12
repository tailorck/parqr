import logging
import json
import pdb

from datetime import datetime
from flask import jsonify, make_response, request
import pandas as pd

from app import app
from app.modeltrain import ModelTrain
from app.models import Course
from exception import InvalidUsage
from parqr import Parqr
from scraper import Scraper

from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler
import rq_dashboard

from tasksrq import test_me

api_endpoint = '/api/'

parqr = Parqr()
scraper = Scraper()
model_train = ModelTrain()

logger = logging.getLogger('app')

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")

redis = Redis(host="redishost", port="6379", db=0)
queue = Queue(connection=redis)
scheduler = Scheduler(connection=redis)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'error not found'}), 400)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    return make_response(jsonify(error.to_dict()), error.status_code)


@app.route('/')
def index():
    return "Hello, World!"


@app.route(api_endpoint + 'event', methods=['POST'])
def register_event():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'eventName' not in request.json:
        pass
    if 'time' not in request.json:
        pass

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
def train_all_models():
    model_train.persist_all_models()
    return jsonify({'msg': 'training all models'}), 202


@app.route(api_endpoint + 'train_model', methods=['POST'])
def train_model():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'course_id' not in request.json:
        raise InvalidUsage('Course ID not found in JSON', 400)

    cid = request.json['course_id']
    model_train.persist_model(cid)

    return jsonify({'course_id': cid}), 202


@app.route(api_endpoint + 'similar_posts', methods=['POST'])
def similar_posts():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'query' not in request.json:
        raise InvalidUsage('No query string found in parameters', 400)
    if 'cid' not in request.json:
        raise InvalidUsage('No cid string found in parameters', 400)
    if 'N' not in request.json:
        N = 5
    else:
        N = int(request.json['N'])

    course_id = request.json['cid']
    if not Course.objects(cid=course_id):
        logger.error('New un-registered course found: {}'.format(course_id))
        raise InvalidUsage("Course with cid {} not supported at this "
                           "time.".format(course_id), 400)

    query = request.json['query']
    similar_posts = parqr.get_recommendations(course_id, query, N)
    return jsonify(similar_posts)


@app.route(api_endpoint + 'class/<cid>', methods=['POST'])
def register_class(cid):
    if not redis.exists(cid):
        job = scheduler.schedule(scheduled_time=datetime.now(), func=test_me, kwargs={"course_id": cid},
                                 interval=10)
        redis.set(cid, str(job.id))
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID already exists', 500)


@app.route(api_endpoint + 'class/<cid>', methods=['DELETE'])
def deregister_class(cid):
    if redis.exists(cid):
        job_id = redis.get(cid)
        redis.delete(cid)
        jobs = filter(lambda job: str(job.id) == job_id, [j for j in scheduler.get_jobs()])
        for job in jobs:
            scheduler.cancel(job)
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID does not exists', 500)