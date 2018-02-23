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
