from flask import request


def verify_non_empty_json_request(func):
    def wrapper(*args, **kwargs):
        if request.get_data() == '':
            raise InvalidUsage('No request body provided', 400)
        if not request.json:
            raise InvalidUsage('Request body must be in JSON format', 400)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def to_dict(exception):
    if hasattr(exception, 'payload') and exception.payload is not None:
        rv = dict(exception.payload)
    else:
        rv = dict()
    rv['message'] = exception.message
    return rv


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
