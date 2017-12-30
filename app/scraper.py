from threading import Thread
import time
import logging

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError
from progressbar import ProgressBar

from exception import InvalidUsage
from models import Course, Post
from utils import read_credentials, stringify_followups


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

    def update_posts(self, course_id):
        """Creates a thread task to update all posts in a course

        Parameters
        ----------
        course_id : str
            The course id of the class to be updated
        """
        if course_id in self._threads and self._threads[course_id].is_alive():
            raise InvalidUsage('Background thread is running', 500)

        # TODO: Catch invalid course_id exception
        network = self._piazza.network(course_id)
        self._threads[course_id] = Thread(target=self._update_posts,
                                          args=(course_id, network,))

        self._threads[course_id].start()

    def _update_posts(self, course_id, network):
        """Retrieves all new posts in course that are not already in database
        and updates old posts that have been modified

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

        start_time = time.time()
        for pid in pbar(xrange(1, total_questions+1)):
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

            # Extract the followups and feedbacks if applicable
            followups = self._extract_followups(post)

            # If post exists, check if it has been updated and update db if
            # necessary. Else, insert new post and add to course's post list
            if Post.objects(cid=course_id, pid=pid):
                db_post = Post.objects.get(cid=course_id, pid=pid)
                new_fields = dict(subject=subject, body=body,
                                  s_answer=s_answer, i_answer=i_answer,
                                  followups=followups)
                is_updated = self._check_for_updates(db_post, new_fields)

                if is_updated is True:
                    db_post.update(subject=subject, body=body,
                                   s_answer=s_answer, i_answer=i_answer,
                                   followups=followups)
            else:
                mongo_post = Post(course_id, pid, subject, body, tags,
                                  s_answer, i_answer, followups).save()
                course.update(add_to_set__posts=mongo_post)

        end_time = time.time()
        time_elapsed = end_time - start_time
        self._logger.info('Course updated. {} posts scraped in: '
                          '{:.2f}s'.format(total_questions, time_elapsed))
        self._threads.pop(course_id)

    def _check_for_updates(self, curr_post, new_fields):
        """Checks if post has been updated since last scrape.

        Parameters
        ----------
        curr_post : app.models.Post
            The current post in the database.
        new_fields : dict
            A dictionary of the most recent scraped fields for the given post

        Returns
        -------
        is_updated : boolean
            True if any of the fields have been changed. Otherwise, False.
        """
        curr_followups_str = stringify_followups(curr_post.followups)
        new_followups_str = stringify_followups(new_fields['followups'])

        if curr_post.subject != new_fields['subject']:
            return True
        elif curr_post.body != new_fields['body']:
            return True
        elif curr_post.s_answer != new_fields['s_answer']:
            return True
        elif curr_post.i_answer != new_fields['i_answer']:
            return True
        elif curr_followups_str != new_followups_str:
            return True

        return False

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
        for response in post['children']:
            if response['type'] == 's_answer':
                html_text = response['history'][0]['content']
                s_answer = BeautifulSoup(html_text, 'html.parser').get_text()
            elif response['type'] == 'i_answer':
                html_text = response['history'][0]['content']
                i_answer = BeautifulSoup(html_text, 'html.parser').get_text()

        return s_answer, i_answer

    def _extract_followups(self, post):
        """Retrieves information pertaining to the followups and feedbacks of
        the piazza post

        Parameters
        ----------
        post : dict
            An object including the post information retrieved from a
            piazza_api call

        Returns
        -------
        followups : list
            The followup discussions for a post if available, which might
            contain feedbacks as well (Default = []).
        """
        followups = []
        for child in post['children']:

            data = {}
            if child['type'] == 'followup':
                html_text = child['subject']
                soup = BeautifulSoup(html_text, 'html.parser')
                data['text'] = soup.get_text()

                responses = []
                if child['children']:
                    for activity in child['children']:
                        html_text = activity['subject']
                        soup = BeautifulSoup(html_text, 'html.parser')
                        responses.append(soup.get_text())

                data['responses'] = responses

                followups.append(data)

        return followups

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
