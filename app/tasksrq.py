from app.modeltrain import ModelTrain
from parser import Parser


def parse_posts(course_id):
    return Parser().update_posts(course_id)


def train_models(course_id):
    return ModelTrain().persist_model(course_id)
