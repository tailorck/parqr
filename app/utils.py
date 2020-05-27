from flask import Flask, request

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
        if request.get_data() == "":
            raise InvalidUsage("No request body provided", 400)
        if not request.json:
            raise InvalidUsage("Request body must be in JSON format", 400)
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime

    now = datetime.now()
    if isinstance(time, int):
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    day_diff = diff.days

    if day_diff < 0:
        return ""
    if day_diff == 0:
        return "today"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + "d ago"
    if day_diff < 31:
        return str(day_diff / 7) + "w ago"
    if day_diff < 365:
        return str(day_diff / 30) + "mon ago"
    return str(day_diff / 365) + "y ago"
