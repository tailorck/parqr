from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction import text
from nltk.corpus import stopwords
from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError
from progressbar import ProgressBar
from threading import Thread
from app.exception import InvalidUsage
import numpy as np
import re


class PARQR():
    def __init__(self, course_id, logger):
        self.p = Piazza()
        while True:
            try:
                self.p.user_login()
                break
            except AuthenticationError:
                continue

        self.logger = logger
        self.background_thread = Thread(target=self.__create_tfidf_matrix)
        self.course = None
        self.posts = None
        self.vectorizer = None
        self.tfidf_matrix = None

        if course_id is not None:
            self.set_course(course_id)

    def set_course(self, course_id):
        """Creates a course object for retreiving course stats and posts

        Args:
            course_id: (str) The course ID found in the URL for the course
        """
        # TODO: Catch invalid course_id exception
        self.logger.info('Setting course to course_id: ' + course_id)
        self.course_id = course_id
        self.course = self.p.network(course_id)
        self.background_thread.start()

    def get_similar_posts(self, query, N):
        """Get the N most similar posts to provided query.

        Args:
            query: (str) A query string to perform comparison on
            N: (int) The number of similar posts to return

        Returns:
            top_posts: A sorted dict of the top N most similar posts with
            their similarity scores (e.g. {1: 2.872, 2: 0.5284, ...})
        """
        self.logger.info('Retrieving similar posts for query: ' + query)
        if self.background_thread.is_alive():
            raise InvalidUsage('Background thread is still running', 500)

        q_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vector, self.tfidf_matrix)[0]
        top_N = np.argsort(scores)[::-1][:N]
        top_posts = {k: v for k, v in zip(top_N, scores[top_N])}
        return top_posts

    def __remove_punctuation_and_numbers(self, string):
        """Removes all non-lowercase or non-uppercase characters from string

        Returns:
            A string without punctuation and numbers
        """
        return re.sub('[^a-zA-Z]', ' ', string)

    def __clean_and_split(self, string):
        """Removes punctuation and returns a list of words in the string"""
        only_letters = self.__remove_punctuation_and_numbers(string)
        return only_letters.lower().strip().split()

    def __get_all_posts(self):
        """Returns a list of strings containing the words from every post in a
        Piazza course.
        """
        self.logger.info('Retrieving all posts from course with id: ' +
                         self.course_id)
        self.posts = []
        stats = self.course.get_statistics()
        pbar = ProgressBar(maxval=stats['total']['questions'])
        for post in pbar(self.course.iter_all_posts()):
            subject = self.__clean_and_split(post['history'][0]['subject'])

            html_body = post['history'][0]['content']
            parsed_body = BeautifulSoup(html_body, 'html.parser').get_text()
            body = self.__clean_and_split(parsed_body)

            tags_list = post['folders']
            self.posts.append(' '.join(subject + body + tags_list))

        self.posts = np.array(self.posts)

    def __vectorize_words(self):
        """Vectorizes the list of post words into a TFIDF Matrix"""
        self.logger.info('Vectorizing words from posts list')
        nltk_stopwords = set(stopwords.words('english'))
        stop_words = text.ENGLISH_STOP_WORDS.union(nltk_stopwords)
        self.vectorizer = text.TfidfVectorizer(stop_words=set(stop_words))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.posts)

    def __create_tfidf_matrix(self):
        """Downloads data for course and vectorizes data into a tfidf matrix"""
        # self.__get_all_posts()
        self.__get_all_posts()
        self.__vectorize_words()
