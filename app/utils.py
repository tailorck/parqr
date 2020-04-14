from flask import Flask, request

from app.config import config_dict
from app.exception import InvalidUsage


def create_app(app_name):
    """Creates a flask object with the appropriate configurations.

    Args:
        app_name (str): The name of the Flask App
    Returns:
        app

    """
    return Flask(app_name)


def verify_non_empty_json_request(func):
    def wrapper(*args, **kwargs):
        if request.get_data() == '':
            raise InvalidUsage('No request body provided', 400)
        if not request.json:
            raise InvalidUsage('Request body must be in JSON format', 400)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper
