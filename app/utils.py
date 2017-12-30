from logging.handlers import RotatingFileHandler
import logging
import os
import re

import numpy as np
from flask import Flask
from Crypto.PublicKey import RSA
from scipy.sparse import save_npz, load_npz
from sklearn.externals import joblib

from config import config_dict


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


def stringify_followups(followup_list):
    return_list = []
    for followup in followup_list:
        return_list.append(followup['text'])
        return_list += followup['responses']

    return ' '.join(return_list)


class ModelCache(object):
    model_fn_format = '{}_vectorizer.pkl'
    matrix_fn_format = '{}_matrix.npz'
    pid_list_fn_format = '{}_pid_list.csv'

    def __init__(self, cache_path):
        self.cache_path = cache_path

        if not os.path.isdir(cache_path):
            logger.warn('Resource path does not exist. Creating {}'
                        .format(cache_path))
            os.mkdir(cache_path)

    def _get_cid_dir(self, cid):
        return os.path.join(self.cache_path, cid)

    def _ensure_dir(self, cid):
        _dir = self._get_cid_dir(cid)

        if not os.path.isdir(_dir):
            os.mkdir(_dir)

        return _dir

    def store_model(self, cid, name, model):
        model_fn = self.model_fn_format.format(name)
        model_dir = self._ensure_dir(cid)
        joblib.dump(model, os.path.join(model_dir, model_fn))

    def store_matrix(self, cid, name, matrix):
        matrix_fn = self.matrix_fn_format.format(name)
        matrix_dir = self._ensure_dir(cid)
        save_npz(os.path.join(matrix_dir, matrix_fn), matrix)

    def store_pid_list(self, cid, name, pid_list):
        pid_list_fn = self.pid_list_fn_format.format(name)
        pid_list_dir = self._ensure_dir(cid)
        np.savetxt(os.path.join(pid_list_dir, pid_list_fn), pid_list)

    def get_all_objects(self, cid, name):
        model = self.get_model(cid, name)
        matrix = self.get_matrix(cid, name)
        pid_list = self.get_pid_list(cid, name)

        return model, matrix, pid_list

    def get_model(self, cid, name):
        model_fn = self.model_fn_format.format(name)
        model_dir = self._get_cid_dir(cid)
        model_file = os.path.join(model_dir, model_fn)

        # TODO: Catch errors around file getters
        if os.path.isfile(model_file):
            model = joblib.load(model_file, 'r')
        else:
            logger.error("Model for cid '{}' with name '{}' not "
                         "found".format(cid, name))
            model = None

        return model

    def get_matrix(self, cid, name):
        matrix_fn = self.matrix_fn_format.format(name)
        matrix_dir = self._get_cid_dir(cid)
        matrix_file = os.path.join(matrix_dir, matrix_fn)

        # TODO: Catch errors around file getters
        if os.path.isfile(matrix_file):
            matrix = load_npz(matrix_file)
        else:
            logger.error("matrix for cid '{}' with name '{}' not "
                         "found".format(cid, name))
            matrix = None

        return matrix

    def get_pid_list(self, cid, name):
        pid_list_fn = self.pid_list_fn_format.format(name)
        pid_list_dir = self._get_cid_dir(cid)
        pid_list_file = os.path.join(pid_list_dir, pid_list_fn)

        # TODO: Catch errors around file getters
        if os.path.isfile(pid_list_file):
            pid_list = np.loadtxt(pid_list_file)
        else:
            logger.error("pid list for cid '{}' with name '{}' not "
                         "found".format(cid, name))
            pid_list = None

        return pid_list
