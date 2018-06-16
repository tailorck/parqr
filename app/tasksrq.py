from app.modeltrain import ModelTrain
from parser import Parser


def parse_and_train_models(course_id):
    Parser().update_posts(course_id)
    ModelTrain().persist_models(course_id)
    return
