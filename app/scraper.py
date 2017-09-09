import re

from threading import Thread
import logging

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError
from progressbar import ProgressBar

from .exception import InvalidUsage
from .models import Course, Post
from .utils import read_credentials


class Scraper():

    def __init__(self, verbose=False):
        """Initialize the Piazza object and login with the encrypted username
        and password

        Parameters
        ----------
        verbose : boolean
            A boolean to instruct module to output informative log statements
        """
        self._piazza = Piazza()
        self._threads = {}
        self.verbose = verbose
        if self.verbose == True:
            self._logger = logging.getLogger('app')

        self._login()

    def pull_new_posts(self, course_id):
        """Creates a thread task to retrieve all new posts for a course

        Parameters
        ----------
        course_id : str
            The course id of the class to be updated
        """
        if course_id in self._threads and self._threads[course_id].is_alive():
            raise InvalidUsage('Background thread is running', 500)

        # TODO: Catch invalid course_id exception
        network = self._piazza.network(course_id)
        self._threads[course_id] = Thread(target=self._pull_new_posts,
                                          args=(course_id, network,))

        self._threads[course_id].start()

    def _pull_new_posts(self, course_id, network):
        """Retrieves all new posts in course that are not already in database

        Parameters
        ----------
        course_id : str
            The course id of the class to be updated
        network : piazza_api.network
            A handle to the network object for the course
        """
        if self.verbose:
            self._logger.info('Retrieving posts for: {}'.format(course_id))
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
                continue

            # Get the post if available
            try:
                post = network.get_post(pid)
            except RequestError:
                continue

            # Skip deleted and private posts
            if post['status'] == 'deleted' or post['status'] == 'private':
                continue

            # Extract the subject, body, and tags from post
            subject, body, tags = self._extract_question_details(post)

            # Extract the student and instructor answers if applicable
            s_answer, i_answer = self._extract_answers(post)

            # Create a new post and add it to the course
            mongo_post = Post(course_id, pid, subject, body, tags, s_answer,
                              i_answer).save()
            course.update(add_to_set__posts=mongo_post)

        self._threads.pop(course_id)

    def _extract_question_details(self, post):
        """Retrieves information pertaining to the question in the piazza post

        Parameters
        ----------
        post : dict
            An object including  post information retrieved from a
            piazza_api call

        Returns
        -------
            subject : str
                The subject of the piazza post
            parsed_body : str
                The body of the post without html tags
            tags : list
                A list of the tags or folders that the post belonged to
        """
        subject = post['history'][0]['subject']
        html_body = post['history'][0]['content']
        parsed_body = BeautifulSoup(html_body, 'html.parser').get_text()
        tags = post['folders']
        return subject, parsed_body, tags

    def _extract_answers(self, post):
        """Retrieves information pertaining to the answers of the piazza post

        Parameters
        ----------
        post : dict
            An object including the post information retrieved from a
            piazza_api call

        Returns
        -------
        s_answer : str
            The student answer to the post if available (Default = None).
        i_answer : str
            The instructor answer to the post if available (Default = None).
        """
        s_answer, i_answer = None, None
        for response in post['children'][:2]:
            if response['type'] == 's_answer':
                html_text = response['history'][0]['content']
                s_answer = BeautifulSoup(html_text, 'html.parser').get_text()
            elif response['type'] == 'i_answer':
                html_text = response['history'][0]['content']
                i_answer = BeautifulSoup(html_text, 'html.parser').get_text()

        return s_answer, i_answer

    def _login(self):
        """Try to read the login file else prompt the user for manual login"""
        try:
            email, password = read_credentials()
            self._piazza.user_login(email, password)
        except IOError:
            if self.verbose:
                self._logger.error("File not found. Use encrypt_login.py to "
                                   "create encrypted password store")
            self._login_with_input()
        except UnicodeDecodeError, AuthenticationError:
            if self.verbose:
                self._logger.error("Incorrect Email/Password found in "
                                   "encryptedfile store")
            self._login_with_input()

        if self.verbose:
            self._logger.info('Ready to serve requests')

    def _login_with_input(self):
        """Prompt the user to input username and password to login to Piazza"""
        while True:
            try:
                self._piazza.user_login()
                break
            except AuthenticationError:
                if self.verbose:
                    self._logger.error('Invalid Username/Password')
                continue
