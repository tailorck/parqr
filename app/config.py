'''
Configuration File

'''
import logging
from datetime import timedelta
from os.path import dirname, abspath, join

file_dir = dirname(abspath(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    LOG_FOLDER = join(file_dir, '..', 'logs')
    JSONSCHEMA_DIR = join(file_dir, 'schemas')
    SECRET_KEY = 'secretsauce'
    JWT_EXPIRATION_DELTA = timedelta(seconds=1800)


class ProductionConfig(Config):
    LOG_LEVEL = logging.INFO
    DEBUG = False
    TESTING = False
    MONGODB_DB = 'parqr'
    MONGODB_HOST = 'mongo'
    MONGODB_PORT = 27017
    REDIS_HOST = 'redishost'
    REDIS_PORT = '6379'


class DevelopmentConfig(Config):
    LOG_LEVEL = logging.DEBUG
    DEBUG = True
    TESTING = False
    MONGODB_DB = 'parqr'
    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017
    REDIS_HOST = 'localhost'
    REDIS_PORT = '6379'


class TestingConfig(Config):
    LOG_LEVEL = logging.DEBUG
    DEBUG = True
    TESTING = True
    MONGODB_DB = 'test_parqr'
    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017
    REDIS_HOST = 'localhost'
    REDIS_PORT = '6379'


config_dict = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig
}
