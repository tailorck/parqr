from app.modeltrain import ModelTrain
from scraper import Scraper


def test_me(course_id):
    cid = Scraper().test(course_id)
    print cid
    return cid


def update_post(course_id):
    return Scraper().update_posts(course_id)


def train_model(course_id):
    return ModelTrain().persist_model(course_id)
