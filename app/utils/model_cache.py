import logging
import os

import numpy as np
from scipy.sparse import save_npz, load_npz
from sklearn.externals import joblib

from app.exception import InvalidUsage

logger = logging.getLogger('app')


class ModelCache(object):
    model_fn_format = '{}_vectorizer.pkl'
    matrix_fn_format = '{}_matrix.npz'
    pid_list_fn_format = '{}_pid_list.csv'

    def __init__(self, cache_path):
        self.cache_path = cache_path

        if not os.path.isdir(cache_path):
            logger.warning('Resource path does not exist. Creating {}'
                           .format(cache_path))
            os.mkdir(cache_path)

    def _get_cid_dir(self, cid):
        cid_dir = os.path.join(self.cache_path, cid)

        if not os.path.isdir(cid_dir):
            error_msg = "No models found for course with cid: {}".format(cid)
            logger.error(error_msg)
            raise InvalidUsage(error_msg)

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

    def get_all(self, cid, name):
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
            logger.debug("Could not find MODEL for cid '{}' with name '{}'"
                         .format(cid, name))
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
            logger.debug("Could not find MATRIX for cid '{}' with name '{}'"
                         .format(cid, name))
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
            logger.debug("Could not find PID_LIST for cid '{}' with "
                         "name '{}'".format(cid, name))
            pid_list = None

        return pid_list
