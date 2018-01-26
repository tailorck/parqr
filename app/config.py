import logging
from os.path import dirname, abspath, join

file_dir = dirname(abspath(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    MONGODB_DB = 'parqr'
    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017
    LOG_FOLDER = join(file_dir, '..', 'logs')


class ProductionConfig(Config):
    LOG_LEVEL = logging.INFO


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
