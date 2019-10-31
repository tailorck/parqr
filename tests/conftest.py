import os

import pytest

#uses fixtures by matching function names with the names of args in the test functions

@pytest.fixture(scope='session', autouse=True)
def test_correct_env():
    print('Making sure FLASK_CONF=testing')
    assert os.environ['FLASK_CONF'] == 'testing'


@pytest.fixture(scope='module')
def client():
    from app import api
    client = api.app.test_client()
    return client