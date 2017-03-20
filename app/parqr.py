from bs4 import BeautifulSoup
from piazza_api import Piazza
from progressbar import ProgressBar
import pdb
import pandas as pd
import re
import os

DATA_FILE_PATH = 'app/static/resources/all_posts_words.csv'


def remove_punctuation_and_numbers(text):
    """Removes all non-lowercase or non-uppercase characters from string"""
    return re.sub('[^a-zA-Z]', ' ', text)


def clean_and_split(text):
    """Removes punctuation and returns a list of words in the string"""
    only_letters = remove_punctuation_and_numbers(text)
    return only_letters.lower().strip().split()


def get_all_posts_as_words(course):
    """Returns a list of strings containing the words from every post in a
    Piazza course.

    :param course: The course for which all posts will be retrieved
    :type course: piazza_api.network.Network
    :returns: A list of strings containing all the words in each post's
        subject,body, and tags
    :rtype: list
    """
    # posts = {}
    posts = []
    stats = course.get_statistics()
    pbar = ProgressBar(maxval=stats['total']['questions'])
    # pbar = ProgressBar()
    for post in pbar(course.iter_all_posts()):
        subject_words = clean_and_split(post['history'][0]['subject'])

        html_body = post['history'][0]['content']
        parsed_body = BeautifulSoup(html_body, 'html.parser').get_text()
        body_words = clean_and_split(parsed_body)

        tags_list = post['folders']
        # posts[post['nr']] = subject_words + body_words + tags_list
        posts.append(' '.join(subject_words+body_words+tags_list))

    return posts


def vectorize_words(posts):
    pass


def words_to_csv(words_dict):
    df = pd.DataFrame.from_dict(words_dict, orient='index')
    df.to_csv(os.path.join(os.path.abspath('.'), DATA_FILE_PATH))


if __name__ == "__main__":
    p = Piazza()
    p.user_login()
    cse6242 = p.network('ixpgu1xccuo47d')
    words_dict = get_all_posts_as_words(cse6242)
    words_to_csv(words_dict)
