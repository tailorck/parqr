from datetime import datetime, timedelta
from collections import namedtuple, defaultdict
import logging
import json

from flask import jsonify, make_response, request
from flask_json_schema import JsonSchema, JsonValidationError

from flask_httpauth import HTTPBasicAuth
from flask_jwt import JWT, jwt_required
from redis import Redis
from rq_scheduler import Scheduler
from flask_cors import CORS, cross_origin

from app import app

from app.models import Course, Event, EventData, User, Post
from app.statistics import (
    get_unique_users,
    number_posts_prevented,
    total_posts_in_course,
    get_inst_att_needed_posts,
    get_stud_att_needed_posts,
    is_course_id_valid
)
from app.constants import (
    COURSE_PARSE_TRAIN_TIMEOUT_S,
    COURSE_PARSE_TRAIN_INTERVAL_S,
    FEEDBACK_MAX_RATING,
    FEEDBACK_MIN_RATING
)
from app.schemas import (
    user,
    course,
    event,
    query,
    train_model,
    feedback_schema
)

from app.tasksrq import parse_and_train_models
from app.exception import InvalidUsage, to_dict
from app.parser import Parser
from app.parqr import Parqr
from app.feedback import Feedback

api_endpoint = '/api/'

parqr = Parqr()
parser = Parser()
schema = JsonSchema(app)

feedback = Feedback(FEEDBACK_MAX_RATING, FEEDBACK_MIN_RATING)
logger = logging.getLogger('app')

redis_host = app.config['REDIS_HOST']
redis_port = app.config['REDIS_PORT']
redis = Redis(host=redis_host, port=redis_port, db=0)
scheduler = Scheduler(connection=redis)
auth = HTTPBasicAuth()

logger.info('Ready to serve requests')

with open('related_courses.json') as f:
    related_courses = json.load(f)
CORS(app)



def verify(username, password):
    print(username)
    Identity = namedtuple('Identity', ['id'])
    user = User.objects(username=username).first()
    if not user or not user.verify_password(password):
        return False
    return Identity(str(user.pk))


def identity(payload):
    user_id = payload['identity']
    return User.objects(pk=user_id).first()


jwt = JWT(app, verify, identity)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'endpoint not found'}), 404)


@app.errorhandler(InvalidUsage)
def on_invalid_usage(error):
    return make_response(jsonify(to_dict(error)), error.status_code)


@app.errorhandler(JsonValidationError)
def on_validation_error(error):
    # return make_response(jsonify(to_dict(error)), 400)
    return jsonify({'error': error.message,
                    'errors': [validation_error.message for validation_error
                               in error.errors]})


def verify_non_empty_json_request(func):
    def wrapper(*args, **kwargs):
        if request.get_data() == '':
            raise InvalidUsage('No request body provided', 400)
        if not request.json:
            raise InvalidUsage('Request body must be in JSON format', 400)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route('/')
def index():
    return "Hello, World!"


@app.route(api_endpoint + 'event', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(event)
def register_event():
    '''
    Define event
    :return:
    '''
    millis_since_epoch = request.json['time'] / 1000.0

    event = Event()
    event.event_type = request.json['type']
    event.event_name = request.json['eventName']
    event.time = datetime.fromtimestamp(millis_since_epoch)
    event.user_id = request.json['user_id']
    event.event_data = EventData(**request.json['eventData'])

    event.save()
    logger.info('Recorded {} event from cid {}'
                .format(event.event_name, event.event_data.course_id))

    return jsonify({'message': 'success'}), 200


@app.route(api_endpoint + 'similar_posts', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(query)
def similar_posts():
    '''
    Given course_id and query, retrieve 5 similar posts
    :return:
    '''
    course_id = request.json['course_id']
    if not Course.objects(course_id=course_id):
        logger.error('New un-registered course found: {}'.format(course_id))
        raise InvalidUsage("Course with course id {} not supported at this "
                           "time.".format(course_id), 400)

    query = request.json['query']
    similar_posts = parqr.get_recommendations(course_id, query, 5)
    if feedback.requires_feedback():
        query_rec_id = feedback.save_query_rec_pair(course_id, query, similar_posts)
        similar_posts = feedback.update_recommendations(query_rec_id, similar_posts)

    return jsonify(similar_posts)


@app.route(api_endpoint + 'answer_recommendations', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(query)
def instructor_rec():
    '''
    Given course_id and query, get related course_ids, get 5 similar posts.


    :return:
    '''
    course_id = request.json['course_id']
    if not Course.objects(course_id=course_id) or course_id not in related_courses:
        logger.error('New un-registered course found: {}'.format(course_id))
        raise InvalidUsage("Course with course id {} not supported at this "
                           "time.".format(course_id), 400)

    query = request.json['query']

    response = defaultdict(list)
    for rel_course_id in related_courses[course_id]:
        if not Course.objects(course_id=rel_course_id):
            continue

        recs = parqr.get_recommendations(rel_course_id, query, 5)
        recs_post_ids = [rec['pid'] for rec in recs.values()]
        recommended_posts = Post.objects(course_id=rel_course_id,
                                         post_id__in=recs_post_ids)

        for post in recommended_posts:
            if post.i_answer is not None:
                response[rel_course_id].append({
                    "post_id": post.post_id,
                    "student_subject": post.subject,
                    "student_post": post.body,
                    "instructor_answer": post.i_answer
                })

    return jsonify(response)


# TODO: Add additional attributes (i.e. professor, classes etc.)
@app.route(api_endpoint + 'class', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(course)
@jwt_required()
def register_class():
    '''
    insturctor registers the class

    :return:
    '''
    cid = request.json['course_id']
    if not redis.exists(cid):
        logger.info('Registering new course: {}'.format(cid))
        curr_time = datetime.now()
        delayed_time = curr_time + timedelta(minutes=5)

        new_course_job = scheduler.schedule(scheduled_time=datetime.now(),
                                            func=parse_and_train_models,
                                            kwargs={"course_id": cid},
                                            interval=COURSE_PARSE_TRAIN_INTERVAL_S,
                                            timeout=COURSE_PARSE_TRAIN_TIMEOUT_S)
        redis.set(cid, new_course_job.id)
        return jsonify({'course_id': cid}), 202
    else:
        raise InvalidUsage('Course ID already exists', 400)


@app.route(api_endpoint + 'class', methods=['DELETE'])
@verify_non_empty_json_request
@schema.validate(course)
@jwt_required()
def deregister_class():
    '''
    Deregister the class

    :return:
    '''
    cid = request.json['course_id']

    if redis.exists(cid):
        logger.info('Deregistering course: {}'.format(cid))
        job_id_str = redis.get(cid)
        scheduler.cancel(job_id_str)
        redis.delete(cid)
        return jsonify({'course_id': cid}), 200
    else:
        raise InvalidUsage('Course ID does not exists', 400)


@app.route(api_endpoint + 'class/<course_id>/usage', methods=['GET'])
def get_parqr_stats(course_id):
    '''
    Get num of unique users, num of post prevented, percent of Traffic reduced

    :param course_id:
    :return:
    '''
    try:
        start_time = int(request.args.get('start_time'))
    except (ValueError, TypeError) as e:
        raise InvalidUsage('Invalid start time specified', 400)
    num_active_uid = get_unique_users(course_id, start_time)
    num_post_prevented, posts_by_parqr_users = number_posts_prevented(course_id, start_time)
    num_total_posts = total_posts_in_course(course_id)
    num_all_post = float(posts_by_parqr_users + num_post_prevented)
    percent_traffic_reduced = (num_post_prevented / num_all_post) * 100
    return jsonify({'usingParqr': num_active_uid,
                    'assistedCount': num_post_prevented,
                    'percentTrafficReduced': percent_traffic_reduced}), 202


@app.route(api_endpoint + 'class/<course_id>/attentionposts', methods=['GET'])
def get_top_inst_posts(course_id):
    '''
    For given course_id and number of posts to get, retrieve posts from starting time to now

    Retrieves the top instructor attention needed posts, for a specific
    course, with the search time being [starting_time, now). The following are
    the factors used in determining if a post warrants attention or not:

    1) There is no Instructor answer for it
    2) There is no student answer for it
    3) There are unanswered followup questions for the post

    :param course_id:
    :return:
    '''
    try:
        num_posts = int(request.args.get('num_posts'))
    except (ValueError, TypeError) as e:
        raise InvalidUsage('Invalid number of posts specified. Please specify '
                           'the number of posts you would like as a GET '
                           'parameter `num_posts`.', 400)
    posts = get_inst_att_needed_posts(course_id, num_posts)
    return jsonify({'posts': posts}), 202


@app.route(api_endpoint + 'class/<course_id>/student_recs', methods=['GET'])
def get_top_stud_posts(course_id):
    try:
        num_posts = int(request.args.get('num_posts'))
    except (ValueError, TypeError):
        raise InvalidUsage('Invalid number of posts specified. Please specify '
                           'the number of posts you would like as a GET '
                           'parameter `num_posts`.', 400)
    posts = get_stud_att_needed_posts(course_id, num_posts)
    return jsonify({'posts': posts}), 202


@app.route(api_endpoint + 'class/isvalid', methods=['GET'])
def get_course_isvalid():
    course_id = request.args.get('course_id')
    is_valid = is_course_id_valid(course_id)
    return jsonify({'valid': is_valid}), 202


@app.route('/api/users', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(user)
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')

    if User.objects(username=username).first() is not None:
        raise InvalidUsage('Username already enrolled', 400)

    user = User(username=username)
    user.hash_password(password)
    user.save()
    return jsonify({'username': user.username}), 201


@app.route('/api/class', methods=['GET'])
@jwt_required()
def get_supported_classes():
    return jsonify(Course.objects.values_list('course_id'))


@app.route('/api/enrolled_classes', methods=['GET'])
@jwt_required()
def get_enrolled_classes():
    return jsonify(parser.get_enrolled_courses())


@app.route(api_endpoint + 'class/parse', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(course)
@jwt_required()
def post_course_trigger_parse():
    '''
    For a given course, update the course model.

    :return:
    '''
    course_id = request.json['course_id']

    if redis.exists(course_id):
        logger.info('Triggering parse for course id {}'.format(course_id))
        successful_parse = parser.update_posts(course_id)

        if successful_parse:
            return jsonify({'message': 'success'}), 200

        else:
            return jsonify({'message': 'failure'}), 500

    else:
        raise InvalidUsage('Course ID does not exists', 400)


@app.route(api_endpoint + 'feedback', methods=['POST'])
@verify_non_empty_json_request
@schema.validate(feedback_schema)
def post_feedback():
    # Validate the feedback data
    course_id, user_id, query_rec_id, feedback_pid, user_rating = Feedback.unpack_feedback(request.json)
    valid, message = feedback.validate_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating)

    # If not failed, return invalid usage
    if not valid:
        raise InvalidUsage("Feedback contains invalid data. " + message, 400)

    success = Feedback.register_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating)

    if success:
        return jsonify({'message': 'success'}), 200

    else:
        return jsonify({'message': 'failure'}), 500
