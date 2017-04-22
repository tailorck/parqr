class Config(object):
    MONGODB_DB = 'parqr'
    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    pass


class TestingConfig(Config):
    TESTING = True
