from datetime import datetime, timedelta
from hashlib import md5
import logging
import pandas as pd

from app import app
from app.modeltrain import ModelTrain
from app.models import Course
from exception import InvalidUsage
from parqr import Parqr

from flask import jsonify, make_response, request
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler
import rq_dashboard

from tasksrq import parse_posts, train_models

api_endpoint = '/api/'

parqr = Parqr()
model_train = ModelTrain()

logger = logging.getLogger('app')

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")

redis = Redis(host="redishost", port="6379", db=0)
queue = Queue(connection=redis)
scheduler = Scheduler(connection=redis)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'error not found'}), 404)


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

    data = dict()
    data['cid'] = request.json['eventData']['cid']
    data['type'] = request.json['eventName']
    data['uid'] = request.json['uid']
    data['time'] = request.json['time']

    df = pd.DataFrame(data, index=[0])

    logger.info('Recorded {} event from cid {}'
                .format(data['type'], data['cid']))

    with open('events.csv', 'a') as outfile:
        df.to_csv(outfile, header=False, index=False)

    return jsonify({'msg': 'success'}), 200


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
    recommendations = parqr.get_recommendations(course_id, query, N)
    return jsonify(recommendations)


# TODO: Add additional attributes (i.e. professor, classes etc.)
@app.route(api_endpoint + 'class', methods=['POST'])
def register_class():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'cid' not in request.json:
        raise InvalidUsage('No cid string found in parameters', 400)

    cid = request.json['cid']
    if not redis.exists(cid):
        curr_time = datetime.now()
        delayed_time = curr_time + timedelta(minutes=2)

        parse_job = scheduler.schedule(scheduled_time=curr_time,
                                       func=parse_posts,
                                       kwargs={"course_id": cid}, interval=300)
        train_job = scheduler.schedule(scheduled_time=delayed_time,
                                       func=train_models,
                                       kwargs={"course_id": cid}, interval=300)
        redis.set(cid, ','.join([parse_job.id, train_job.id]))
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID already exists', 500)


@app.route(api_endpoint + 'class', methods=['DELETE'])
def deregister_class():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'cid' not in request.json:
        raise InvalidUsage('No cid string found in parameters', 400)

    cid = request.json['cid']
    if redis.exists(cid):
        job_id_strs = redis.get(cid)
        jobs = filter(lambda job: str(job.id) in job_id_strs,
                      [j for j in scheduler.get_jobs()])
        for job in jobs:
            scheduler.cancel(job)
        redis.delete(cid)
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID does not exists', 500)
