from app import app
from app.exception import InvalidUsage
from flask import jsonify, make_response, request, url_for
from piazza_api import Piazza
from app.parqr import PARQR
import sys
import logging

version = '1.0'
api_endpoint = '/api/v{}/'.format(version)

parqr = PARQR('ixpgu1xccuo47d', app.logger)

sample_post = {
    'folders': 'h2q4',
    'history': [{
        'anon': u'stud',
        'content': u'<p>I am trying to read the zip code values</p>',
        u'created': u'2017-03-02T20:10:11Z',
        u'subject': u'CSV reading zipcode',
        u'uid':
        u'hz1jr5fxbj16y'}]
}


'''
@celery.task(bind=True)
def create_matrix_async(self):
    # the instance that actually runs isn't the same instance where you call
    # the delay method. Every worker instantiates it's own singleton for each
    # task.
    parqr.create_tfidf_matrix(self)
'''


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'error not found'}), 400)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    return make_response(jsonify(error.to_dict()), error.status_code)


@app.route('/')
def index():
    return "Hello, World!"


@app.route(api_endpoint + 'course', methods=['POST'])
def update_course():
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 500)
    if 'course_id' not in request.json:
        raise InvalidUsage('Course ID not found in JSON', 500)

    course_id = request.json['course_id']
    parqr.set_course(course_id)
    return jsonify({'course_id': course_id}), 202


@app.route(api_endpoint + 'similar_posts', methods=['POST'])
def similar_posts():
    # localhost:5000/api/v1.0/similar_posts&keywords=hey&keywords=hi
    # sample_post['keywords'] = request.args.getlist('keywords')
    if not request.json:
        raise InvalidUsage('Request body must be in JSON format', 500)
    if 'query' not in request.json:
        raise InvalidUsage('No query string found in parameters', 500)

    try:
        N = int(request.json['N']) if 'N' in request.json else 5
        query = request.json['query']
        similar_posts = parqr.get_similar_posts(query, N)
        return jsonify(similar_posts)
    except ValueError:
        raise InvalidUsage('N parameter must be an integer', 500)
