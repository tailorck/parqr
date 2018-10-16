from logging.handlers import RotatingFileHandler
import logging
import os

from flask import Flask
import rq_dashboard
from Crypto.PublicKey import RSA

from ..config import config_dict

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
    app = Flask('app')

    # First import the default settings from rq_dashboard to monitor redis
    # queues on the web.
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
    with open('.key.pem') as f:
        key = RSA.importKey(f.read())

    with open('.login') as f:
        email_bytes = f.read(128)
        password_bytes = f.read(128)

    return key.decrypt(email_bytes), key.decrypt(password_bytes)
