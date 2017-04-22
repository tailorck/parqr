from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError
from app.exception import InvalidUsage
from progressbar import ProgressBar
from threading import Thread
from models import Course, Post
from Crypto.PublickKey import RSA
import re
import os


class Scraper():

    def __init__(self, logger):
        self._piazza = Piazza()
        self._logger = logger
        self._threads = {}

        self._login()

    def update_course(self, course_id):
        """Creates a course object for retreiving course stats and posts

        Args:
            course_id: (str) The course ID found in the URL for the course
        """
        # TODO: Catch invalid course_id exception
        if course_id in self._threads and self._threads[course_id].is_alive():
            raise InvalidUsage('Background thread is running', 500)

        network = self._piazza.network(course_id)
        self._threads[course_id] = Thread(target=self._update_course,
                                          args=(course_id, network,))

        self._threads[course_id].start()

    def _update_course(self, course_id, network):
        """Returns a list of strings containing the words from every post in a
        Piazza course.
        """
        self._logger.debug('Retrieving posts for: {}'.format(course_id))
        stats = network.get_statistics()
        total_questions = stats['total']['questions']
        pbar = ProgressBar(maxval=total_questions)

        # Get handle to the corresponding course document or create a new one
        course = Course.objects(cid=course_id)
        if not course:
            course = Course(course_id).save()

        for pid in pbar(xrange(1, total_questions)):
            # skip this post if it is already in the database
            if Post.objects(cid=course_id, pid=pid):
                self._logger.debug('Skipping post with pid: {}'.format(pid))
                continue

            # Get the post if available
            try:
                post = network.get_post(pid)
            except RequestError:
                self._logger.debug('Could not find pid: {}'.format(pid))
                continue

            # Skip deleted and private posts
            if post['status'] == 'deleted' or post['status'] == 'private':
                continue

            # Extract the subject, body, and tags from post
            subject = post['history'][0]['subject']
            html_body = post['history'][0]['content']
            parsed_body = BeautifulSoup(html_body, 'html.parser').get_text()
            tags = post['folders']

            # Create a new post and add it to the course
            self._logger.debug('Inserting post with pid: {}'.format(pid))
            post = Post(course_id, pid, subject, parsed_body, tags).save()
            course.update(add_to_set__posts=post)

        self._threads.pop(course_id)

    def _login(self):
        # TODO: login without user input
        paht = os.path.join(os.path.expanduser('~'), '.ssh/id_rsa.pub')
        try:
            pass
        except IOError:
            self._logger.error("File not found")
            while True:
                try:
                    self._piazza.user_login()
                    break
                except AuthenticationError:
                    self._logger.error('Invalid Username/Password')
                    continue
        self._logger.debug('Ready to serve requests')
