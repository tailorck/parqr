from logging.handlers import RotatingFileHandler
import logging
import os
import re

from flask import Flask
from Crypto.PublicKey import RSA

from config import config_dict


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
    app.config.from_object(config_dict[config_name])

    log_file = os.path.join(app.config['LOG_FOLDER'], 'app.log')
    log_level = app.config['LOG_LEVEL']
    fh = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s '
                                  '%(module)-10s: %(message)s')
    app.logger.addHandler(fh)
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
    app.logger.setLevel(log_level)

    return app


def clean(string):
    """Cleans an input string of nonessential characters for TF-IDF

    Removes all punctuation and numbers from string before converting all upper
    case characters to lower case

    Parameters
    ----------
    string : str
        The input string that needs cleaning

    Returns
    -------
    cleaned_string : str
        The cleaned version of input string
    """
    only_letters = re.sub('[^a-zA-Z]', ' ', string)
    cleaned_string = only_letters.lower().strip()
    return cleaned_string


def clean_and_split(string):
    """Cleans an input string of nonessential characters and converts to list

    Parameters
    ----------
    string : str
        The input string that needs cleaning

    Returns
    -------
    split_string : str
        The cleaned string split up into a list by whitespace
    """
    return clean(string).split()


def read_credentials():
    """Method to read encrypted .login file for Piazza username and password"""
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(curr_dir, '..', '.key.pem')
    login_file = os.path.join(curr_dir, '..', '.login')

    with open('.key.pem') as f:
        key = RSA.importKey(f.read())

    with open('.login') as f:
        email_bytes = f.read(128)
        password_bytes = f.read(128)

    return key.decrypt(email_bytes), key.decrypt(password_bytes)
