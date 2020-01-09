from logging.handlers import RotatingFileHandler
import logging
import os

from flask import Flask, request
import rq_dashboard

from app.config import config_dict
from app.exception import InvalidUsage

logger = logging.getLogger('app')


def create_app(config_name):
    """Creates a flask object with the appropriate configurations.

    Parameters
    ----------
    config_name : str
        config_name is a string to declare the type of configuration to put the
        application in. It is one of ['development', 'production', 'testing'].

    Returns
    -------
    app : Flask object
    """
    app = Flask("app")

    # First import the default settings from rq_dashboard to monitor redis queues on the web.
    app.config.from_object(rq_dashboard.default_settings)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='/rq')

    # Override some parameters of rq_dashboard config with app.config
    app.config.from_object(config_dict[config_name])

    if not os.path.isdir(app.config['LOG_FOLDER']):
        os.makedirs(app.config['LOG_FOLDER'])

    log_file = os.path.join(app.config['LOG_FOLDER'], 'app.log')
    log_level = app.config['LOG_LEVEL']
    fh = RotatingFileHandler(log_file, maxBytes=100*1024*1024, backupCount=5)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s '
                                  '%(module)s: %(message)s')
    app.logger.addHandler(fh)
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
    app.logger.setLevel(log_level)

    return app


def read_credentials():
    """Method to read encrypted .login file for Piazza username and password"""
    return 'parqrdevteam@gmail.com', 'parqrproducers'


def verify_non_empty_json_request(func):
    def wrapper(*args, **kwargs):
        if request.get_data() == '':
            raise InvalidUsage('No request body provided', 400)
        if not request.json:
            raise InvalidUsage('Request body must be in JSON format', 400)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper
