import time
import json
import os

import pytest


@pytest.fixture
def client():
    from app import api
    client = api.app.test_client()
    return client


@pytest.fixture
def Post():
    from app.models import Post
    Post.drop_collection()
    return Post


@pytest.fixture
def Course():
    from app.models import Course
    Course.drop_collection()
    return Course


@pytest.fixture
def dummy_db(client):
    payload = dict(course_id='j8rf9vx65vl23t')
    client.post('/api/course', data=json.dumps(payload),
                content_type='application/json')
    time.sleep(3)


def test_hello_world(client):
    resp = client.get('/')
    assert resp.data == 'Hello, World!'


# The order of these tests is important. test_update_course must come before
# test_similar_posts
def test_update_course(client, Post, Course):
    Post.objects(cid='j8rf9vx65vl23t').delete()
    Course.objects(cid='j8rf9vx65vl23t').delete()

    endpoint = '/api/course'

    # test empty body, no content-type
    resp = client.post(endpoint)
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No request body provided'

    # test empty body, valid content-type
    resp = client.post(endpoint, content_type='application/json')
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No request body provided'

    # test valid course_id
    payload = dict(course_id='j8rf9vx65vl23t')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    time.sleep(3)
    json_resp = json.loads(resp.data)
    assert json_resp['course_id'] == 'j8rf9vx65vl23t'
    assert Course.objects().first().cid == 'j8rf9vx65vl23t'
    assert len(Post.objects()) != 0


def test_similar_posts(client, Post, Course, dummy_db):
    endpoint = '/api/similar_posts'

    # test empty body, no content-type
    resp = client.post(endpoint)
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No request body provided'

    # test empty body valid content-type
    resp = client.post(endpoint, content_type='application/json')
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No request body provided'

    # test valid N, no cid, valid query
    payload = dict(N=5, query='minimax')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No cid string found in parameters'

    # test valid N, valid cid, no query
    payload = dict(N=3, cid='j8rf9vx65vl23t')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == 'No query string found in parameters'

    # test valid N, valid cid, valid query
    payload = dict(N=3, cid='j8rf9vx65vl23t', query='minimax')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 200

    # test valid N, invalid cid, valid query
    payload = dict(N=3, cid='abc123', query='minimax')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 400
