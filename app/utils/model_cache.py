import cPickle as pickle
import logging
import os

import numpy as np
from redis import Redis
from scipy.sparse import save_npz, load_npz
from sklearn.externals import joblib


logger = logging.getLogger('app')
redis = Redis(host="redishost", port="6379", db=0)


class ModelCache(object):
    model_key_format = '{}_{}_vectorizer'
    matrix_key_format = '{}_{}_matrix'
    pid_list_key_format = '{}_{}_pid_list'

    def __init__(self):
        pass

    def store_model(self, cid, name, model):
        key = self.model_key_format.format(cid, name)
        redis.set(key, pickle.dumps(model))

    def store_matrix(self, cid, name, matrix):
        key = self.matrix_key_format.format(cid, name)
        redis.set(key, pickle.dumps(matrix))

    def store_pid_list(self, cid, name, pid_list):
        key = self.pid_list_key_format.format(cid, name)
        redis.set(key, pickle.dumps(pid_list))

    def get_all(self, cid, name):
        model = self.get_model(cid, name)
        matrix = self.get_matrix(cid, name)
        pid_list = self.get_pid_list(cid, name)

        return model, matrix, pid_list

    def get_model(self, cid, name):
        key = self.model_key_format.format(cid, name)

        if redis.exists(key):
            model = pickle.loads(redis.get(key))
        else:
            logger.debug("Could not find MODEL for cid '{}' with "
                         "name '{}'".format(cid, name))
            model = None

        return model

    def get_matrix(self, cid, name):
        key = self.matrix_key_format.format(cid, name)

        if redis.exists(key):
            matrix = pickle.loads(redis.get(key))
        else:
            logger.debug("Could not find MATRIX for cid '{}' with "
                         "name '{}'".format(cid, name))
            matrix = None

        return matrix

    def get_pid_list(self, cid, name):
        key = self.pid_list_key_format.format(cid, name)

        if redis.exists(key):
            pid_list = pickle.loads(redis.get(key))
        else:
            logger.debug("Could not find PID_LIST for cid '{}' with "
                         "name '{}'".format(cid, name))
            pid_list = None

        return pid_list
