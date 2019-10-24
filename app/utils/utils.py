from logging.handlers import RotatingFileHandler
import logging
import os

from flask import Flask
import rq_dashboard

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
    app = Flask(__name__)

    # First import the default settings from rq_dashboard to monitor redis
    # queues on the web.
    app.config.from_object(rq_dashboard.default_settings)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='/rq')

    '''
    Import and register the blueprint from the factory using app.register_blueprint(). 
    Place the new code at the end of the factory function before returning the app.
    
    When a blueprint is registered, 
    any view functions, templates, static files, error handlers, etc. are connected to the app
    
    The error blueprint will have views to (functionality of app)
    '''
    # from app.errors import bp as errors_bp
    # app.register_blueprint(errors_bp)
    #
    # from app.auth import bp as auth_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')

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
