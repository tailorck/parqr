"""Extensions registry
All extensions here are used as singletons and
initialized in application factory
"""
from collections import namedtuple
import logging

from flask_jwt import JWT
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from redis import Redis
from rq_scheduler import Scheduler

from app import app
from app.parser import Parser
from app.parqr import Parqr
from app.models.user import User
from app.feedback import Feedback
from app.constants import (
    FEEDBACK_MAX_RATING,
    FEEDBACK_MIN_RATING
)


def verify(username, password):
    Identity = namedtuple('Identity', ['id'])
    user = User.objects(username=username).first()
    if not user or not user.verify_password(password):
        return False
    return Identity(str(user.pk))


def identity(payload):
    user_id = payload['identity']
    return User.objects(pk=user_id).first()


jwt = JWT(app, verify, identity)
parqr = Parqr()
parser = Parser()
logger = logging.getLogger('app')
redis_host = app.config['REDIS_HOST']
redis_port = app.config['REDIS_PORT']
feedback = Feedback(FEEDBACK_MAX_RATING, FEEDBACK_MIN_RATING)

redis = Redis(host=redis_host, port=redis_port, db=0)
scheduler = Scheduler(connection=redis)
auth = HTTPBasicAuth()
logger.info('Ready to serve requests')


CORS(app)
