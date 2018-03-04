import logging
from os.path import dirname, abspath, join

file_dir = dirname(abspath(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    MONGODB_DB = 'parqr'
    MONGODB_HOST = 'mongo'
    MONGODB_PORT = 27017
    LOG_FOLDER = join(file_dir, '..', 'logs')


class ProductionConfig(Config):
    LOG_LEVEL = logging.INFO
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    LOG_LEVEL = logging.DEBUG
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    LOG_LEVEL = logging.DEBUG
    DEBUG = True
    TESTING = True
    MONGODB_DB = 'test_parqr'


config_dict = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig
}
