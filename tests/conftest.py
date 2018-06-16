import os

import pytest


@pytest.fixture(scope='session', autouse=True)
def test_correct_env():
    print 'Making sure FLASK_CONF=testing'
    assert os.environ['FLASK_CONF'] == 'testing'


@pytest.fixture(scope='module')
def client():
    from app import api
    client = api.app.test_client()
    return client
