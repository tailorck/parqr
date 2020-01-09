from collections import namedtuple
import time
import json

from mock import patch, call
import pytest


@pytest.fixture
def Post():
    from app.models import post
    post.drop_collection()
    return post


@pytest.fixture
def Course():
    from app.models import course
    course.drop_collection()
    return course


@pytest.fixture
def dummy_db(client):
    payload = dict(course_id='j8rf9vx65vl23t')
    client.post('/api/course', data=json.dumps(payload),
                content_type='application/json')
    time.sleep(3)

@pytest.fixture
def dummy_jobs():
    Job = namedtuple('Job', ['id'])
    return [Job('job_id1'), Job('job_id2')]


@patch('app.api.get_unique_users')
@patch('app.api.number_posts_prevented')
@patch('app.api.total_posts_in_course')
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_get_parqr_stats(mock_total_posts, mock_prevented_posts,
                         mock_unique_users, client):
    course_id = 'j8rf9vx65vl23t'
    start_time = 1524417360
    endpoint = '/api/class/{cid}/usage?start_time={time}'.format(cid=course_id,
                                                                 time=start_time)

    mock_unique_users.return_value = 50
    mock_prevented_posts.return_value = 20
    mock_total_posts.return_value = 600
    resp = client.get(endpoint)
    json_resp = json.loads(resp.data)

    mock_unique_users.assert_called_with(course_id, start_time)
    mock_prevented_posts.assert_called_with(course_id, start_time)
    mock_total_posts.assert_called_with(course_id, start_time)

    assert resp.status_code == 202
    assert json_resp['usingParqr'] == 50
    assert json_resp['assistedCount'] == 20
    assert json_resp['percentTrafficReduced'] == (20 / float(600 + 20)) * 100


@patch('app.api.get_top_attention_warranted_posts')
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_get_top_posts(mock_top_posts, client):
    course_id = 'j8rf9vx65vl23t'
    num_posts = 10
    endpoint = '/api/class/{cid}/attentionposts?num_posts={num_posts}'.format(cid=course_id,
                                                            num_posts=num_posts)

    post_properties = [ '5 unresolved followups', '120 views',
                        '3 good questions', 'No instructor answer']
    result = [
        {
            "pid"       :  295,
            "title"     :  "Help with Minimax",
            "properties":  post_properties
        },

        {
            "pid"       : 300,
            "title"     : "Markov Decision Processes Challenge",
            "properties": post_properties
        }
    ]

    mock_top_posts.return_value = result
    resp = client.get(endpoint)
    json_resp = json.loads(resp.data)
    mock_top_posts.assert_called_with(course_id, num_posts)

    assert resp.status_code == 202
    assert json_resp['posts'] == result


@patch('app.api.is_course_id_valid')
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_get_course_isvalid(mock_is_valid_cid, client):
    course_id = 'j8rf9vx65vl23t'
    endpoint = '/api/class/isvalid?course_id={cid}'.format(cid=course_id)

    mock_is_valid_cid.return_value = False
    resp = client.get(endpoint)
    json_resp = json.loads(resp.data)
    mock_is_valid_cid.assert_called_with(course_id)

    assert resp.status_code == 202
    assert json_resp['valid'] == False


@patch('app.api.scheduler')
@patch('app.api.redis')
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_register_class(mock_redis, mock_scheduler, client, dummy_jobs):
    endpoint = '/api/class'
    course_id = 'j8rf9vx65vl23t'
    payload = dict(course_id=course_id)

    # case 1: cid does not exist, register cid
    mock_redis.exists.return_value = False
    mock_scheduler.schedule.side_effect = dummy_jobs
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    mock_redis.set.assert_called_with(course_id,
                                      ','.join([job.id for job in dummy_jobs]))
    assert resp.status_code == 200
    assert json_resp['course_id'] == course_id
    assert mock_scheduler.schedule.call_count == 2

    # case 2: cid exists, do not register cid
    mock_redis.reset_mock()
    mock_scheduler.reset_mock()
    mock_redis.exists.return_value = True
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    assert resp.status_code == 500
    assert mock_scheduler.schedule.call_count == 0


@patch('app.api.scheduler')
@patch('app.api.redis')
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_deregister_class(mock_redis, mock_scheduler, client, dummy_jobs):
    endpoint = '/api/class'
    course_id = 'j8rf9vx65vl23t'
    payload = dict(course_id=course_id)

    # case 1: cid exists, deregister cid
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = ','.join([job.id for job in dummy_jobs])
    mock_scheduler.get_jobs.return_value = dummy_jobs

    resp = client.delete(endpoint, data=json.dumps(payload),
                         content_type='application/json')
    json_resp = json.loads(resp.data)

    calls = [call(job) for job in dummy_jobs]
    mock_redis.get.assert_called_with(course_id)
    mock_scheduler.cancel.assert_has_calls(calls)
    mock_redis.delete.assert_called_with(course_id)
    assert resp.status_code == 200

    # case 2: cid does not exist, catch exception
    mock_redis.reset_mock()
    mock_scheduler.reset_mock()
    mock_redis.exists.return_value = False
    resp = client.delete(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    assert resp.status_code == 500
    assert mock_scheduler.cancel.call_count == 0
    assert mock_redis.delete.call_count == 0

# The order of these tests is important. test_update_course must come before
# test_similar_posts
@pytest.mark.skip(reason='Need to mock out database and queue interactions')
def test_update_course(client, Post, Course):
    Post.objects(course_id='j8rf9vx65vl23t').delete()
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


@pytest.mark.skip(reason='Need to mock out database and queue interactions')
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
    assert json_resp['message'] == "u'course_id' is a required property"

    # test valid N, valid cid, no query
    payload = dict(N=3, course_id='j8rf9vx65vl23t')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    json_resp = json.loads(resp.data)
    assert json_resp['message'] == "u'query' is a required property"

    # test valid N, valid cid, valid query
    payload = dict(N=3, course_id='j8rf9vx65vl23t', query='minimax')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 200

    # test valid N, invalid cid, valid query
    payload = dict(N=3, course_id='abc123', query='minimax')
    resp = client.post(endpoint, data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 400
