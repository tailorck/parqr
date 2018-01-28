from app import app
from app.modeltrain import ModelTrain
from exception import InvalidUsage
from flask import jsonify, make_response, request
from parqr import Parqr
from scraper import Scraper

api_endpoint = '/api/'

parqr = Parqr()
scraper = Scraper()
model_train = ModelTrain()


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'error not found'}), 400)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    return make_response(jsonify(error.to_dict()), error.status_code)


@app.route('/')
def index():
    return "Hello, World!"


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


@app.route(api_endpoint + 'course', methods=['POST'])
def update_course():
    if request.get_data() == '':
        raise InvalidUsage('No request body provided', 400)
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 400)
    if 'course_id' not in request.json:
        raise InvalidUsage('Course ID not found in JSON', 400)

    course_id = request.json['course_id']
    scraper.update_posts(course_id)
    return jsonify({'course_id': course_id}), 202


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

    query = request.json['query']
    cid = request.json['cid']
    similar_posts = parqr.get_recommendations(cid, query, N)
    return jsonify(similar_posts)
