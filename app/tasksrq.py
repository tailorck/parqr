from app.modeltrain import ModelTrain
from app.parser import Parser


def parse_and_train_models(course_id):
    # Only train models if posts are parsed without errors.
    if Parser().update_posts(course_id):
        ModelTrain().persist_models(course_id)
    return
