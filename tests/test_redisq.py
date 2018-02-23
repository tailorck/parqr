import time
import json
import os

import mock
import unittest
import pytest

from app.api import app, register_class, deregister_class

from redis import Redis
from rq.job import Job
from rq import Queue, SimpleWorker
from rq_scheduler import Scheduler


endpoint = '/api/class'
course_id = 'j65vl23t'
payload = dict(cid=course_id)


@mock.patch('app.api.redis')
def test_redis_exists(mock_redis, client):

    # case 1: cid does not exist, register cid
    mock_redis.exists.return_value = False
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_redis.exists.called == True, \
        "Failed to call redis.exists(cid) in register_class"
    mock_redis.exists.assert_called_with(course_id)
    mock_redis.reset_mock()

    # case 2: cid exists, do not register cid
    mock_redis.exists.return_value = True
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_redis.exists.called == True, \
        "Failed to call redis.exists(cid) in register_class"
    mock_redis.reset_mock()

    # case 3: cid exists, deregister cid
    mock_redis.exists.return_value = True
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.exists.called == True, \
        "Failed to call redis.exists(cid) in deregister_class"
    mock_redis.exists.assert_called_with(course_id)
    mock_redis.reset_mock()

    # case 4: cid does not exist, cannot deregister cid
    mock_redis.exists.return_value = False
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.exists.called == True, \
        "Failed to call redis.exists(cid) in deregister_class"


@mock.patch('app.api.redis')
def test_redis_get(mock_redis, client):

    # case 1: cid does not exist, cannot deregister cid
    mock_redis.exists.return_value = False
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.get.called == False, \
        "Failed to not call redis.get(cid) in deregister_class"
    mock_redis.reset_mock()

    # case 2: cid , deregister cid
    mock_redis.exists.return_value = True
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.get.called == True, \
        "Failed to call redis.get(cid) in deregister_class"
    mock_redis.get.assert_called_with(course_id)


@mock.patch('app.api.redis')
def test_redis_set(mock_redis, client):

    # case 1: cid does not exist, register cid
    mock_redis.exists.return_value = False
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_redis.set.called == True, \
        "Failed to call redis.set(cid, serial_ids) in register_class"
    mock_redis.reset_mock()

    # case 2: cid exists, do not register cid
    mock_redis.exists.return_value = True
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_redis.set.called == False, \
        "Failed to not call redis.set(cid, serial_ids) in register_class"


@mock.patch('app.api.redis')
def test_redis_delete(mock_redis, client):

    # case 1: cid exists, deregister cid
    mock_redis.exists.return_value = True
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.delete.called == True, \
        "Failed to call redis.delete(cid) in deregister_class"
    mock_redis.delete.assert_called_with(course_id)
    mock_redis.reset_mock()

    # case 2: cid does not exist, cannot deregister cid
    mock_redis.exists.return_value = False
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_redis.delete.called == False, \
        "Failed to not call redis.delete(cid) in deregister_class"


@mock.patch('app.api.scheduler')
@mock.patch('app.api.redis')
def test_scheduler_schedule(mock_redis, mock_scheduler, client):

    # case 1: cid does not exist, register cid
    mock_redis.exists.return_value = False
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_scheduler.schedule.called == True, \
        "Failed to call scheduler.schedule in register_class"
    mock_redis.reset_mock()
    mock_scheduler.reset_mock()

    # case 2: cid exists, cannot register cid
    mock_redis.exists.return_value = True
    client.post(endpoint, data=json.dumps(payload),
                content_type='application/json')
    assert mock_scheduler.schedule.called == False, \
        "Failed to not call scheduler.schedule in register_class"


@mock.patch('app.api.scheduler')
@mock.patch('app.api.redis')
def test_scheduler_get_jobs(mock_redis, mock_scheduler, client):

    # case 1: cid exists, deregister cid
    mock_redis.exists.return_value = True
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_scheduler.get_jobs.called == True, \
        "Failed to call scheduler.get_jobs in deregister_class"
    mock_redis.reset_mock()
    mock_scheduler.reset_mock()

    # case 2: cid does not exist, cannot deregister cid
    mock_redis.exists.return_value = False
    client.delete(endpoint, data=json.dumps(payload),
                  content_type='application/json')
    assert mock_scheduler.get_jobs.called == False, \
        "Failed to not call scheduler.get_jobs in register_class"