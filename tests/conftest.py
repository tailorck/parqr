import os

import pytest


@pytest.fixture(scope='session', autouse=True)
def test_correct_env():
    print 'Making sure FLASK_CONF=testing'
    assert os.environ['FLASK_CONF'] == 'testing'

# these are just some fun dividiers to make the output pretty
# completely unnecessary, I was just playing with autouse fixtures
@pytest.fixture(scope="function", autouse=True)
def divider_function(request):
    print('\n        --- function %s() start ---' % request.function.__name__)
    def fin():
            print('        --- function %s() done ---' % request.function.__name__)
    request.addfinalizer(fin)

@pytest.fixture(scope="module", autouse=True)
def divider_module(request):
    print('\n    ------- module %s start ---------' % request.module.__name__)
    def fin():
            print('    ------- module %s done ---------' % request.module.__name__)
    request.addfinalizer(fin)

@pytest.fixture(scope="session", autouse=True)
def divider_session(request):
    print('\n----------- session start ---------------')
    def fin():
            print('----------- session done ---------------')
    request.addfinalizer(fin)
