from scraper import Scraper


def test_me(course_id):
    cid = Scraper().test(course_id)
    print cid
    return cid


def train_model(course_id):
    cid = Scraper().update_posts(course_id)
