import time
import logging

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError
from progressbar import ProgressBar

from app.models import Course, Post
from app.utils import read_credentials, stringify_followups

logger = logging.getLogger('app')


class Parser(object):

    def __init__(self):
        """Initialize the Piazza object and login with the encrypted username
        and password
        """
        self._piazza = Piazza()
        self._login()

    def get_enrolled_courses(self):
        enrolled_courses = self._piazza.get_user_classes()
        return [{'name': d['name'], 'course_id': d['nid'], 'term': d['term'],
                 'course_num': d['num']} for d in enrolled_courses]

    def update_posts(self, course_id):
        """Creates a thread task to update all posts in a course

        Retrieves all new posts in course that are not already in database
        and updates old posts that have been modified

        Parameters
        ----------
        course_id : str
            The course id of the class to be updated


        Returns
        -------
        success : boolean
            True if course parsed without any errors. False, otherwise.
        """
        logger.info("Parsing posts for course: {}".format(course_id))
        network = self._piazza.network(course_id)
        stats = network.get_statistics()

        try:
            total_questions = stats['total']['questions']
            pbar = ProgressBar(maxval=total_questions)
        except KeyError:
            logger.error('Unable to get valid statistics for course_id: {}'
                         .format(course_id))
            return False

        # Get handle to the corresponding course document or create a new one
        course = Course.objects(course_id=course_id)
        if not course:
            course = Course(course_id).save()

        start_time = time.time()
        for pid in pbar(xrange(1, total_questions + 1)):
            # Get the post if available
            try:
                post = network.get_post(pid)
            except RequestError:
                continue

            # Skip deleted and private posts
            if post['status'] == 'deleted' or post['status'] == 'private':
                continue

            # TODO: Parse the type of the post, to indicate if the post is
            # a note/announcement

            # Extract the subject, body, and tags from post
            subject, body, tags = self._extract_question_details(post)

            # Extract number of unique views of the post
            num_views = post['unique_views']

            # Extract number of unresolved followups (if any)
            num_unresolved_followups = self._extract_num_unresolved(post)

            # Extract the student and instructor answers if applicable
            s_answer, i_answer = self._extract_answers(post)

            # Extract the followups and feedbacks if applicable
            followups = self._extract_followups(post)

            # If post exists, check if it has been updated and update db if
            # necessary. Else, insert new post and add to course's post list
            if Post.objects(course_id=course_id, post_id=pid):
                db_post = Post.objects.get(course_id=course_id, post_id=pid)
                new_fields = dict(subject=subject, body=body,
                                  s_answer=s_answer, i_answer=i_answer,
                                  followups=followups,
                                  num_unresolved_followups=num_unresolved_followups,
                                  num_views=num_views)
                is_updated = self._check_for_updates(db_post, new_fields)

                if is_updated is True:
                    db_post.update(subject=subject, body=body,
                                   s_answer=s_answer, i_answer=i_answer,
                                   followups=followups,
                                   num_unresolved_followups=num_unresolved_followups,
                                   num_views=num_views)
            else:
                mongo_post = Post(course_id, pid, subject, body, tags,
                                  s_answer, i_answer, followups, num_views,
                                  num_unresolved_followups).save()
                course.update(add_to_set__posts=mongo_post)

        # TODO: Figure out another way to verify whether the current user has
        # access to a class.
        # In the event the course_id was invalid or no posts were parsed,
        # delete course object
        if Post.objects(course_id=course_id).count() == 0:
            logger.error('Unable to parse posts for course: {}. Please '
                         'confirm that the piazza user has access to this '
                         'course'.format(course_id))
            Course.objects(course_id=course_id).delete()
            return False

        end_time = time.time()
        time_elapsed = end_time - start_time
        logger.info('Course updated. {} posts scraped in: '
                    '{:.2f}s'.format(total_questions, time_elapsed))

        return True

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
        elif curr_post.num_views != new_fields['num_views']:
            return True
        elif curr_post.num_unresolved_followups != new_fields['num_unresolved_followups']:
            return True

        return False

    def _extract_num_unresolved(self, post):
        if len(post['children']) > 0:
            unresolved_list = [post['children'][i]['no_answer']
                               for i in range(len(post['children']))
                               if post['children'][i]['type'] == 'followup']
            return sum(unresolved_list)
        else:
            return 0

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
            logger.error("File not found. Use encrypt_login.py to "
                         "create encrypted password store")
            self._login_with_input()
        except UnicodeDecodeError, AuthenticationError:
            logger.error("Incorrect Email/Password found in "
                         "encrypted file store")
            self._login_with_input()

    def _login_with_input(self):
        """Prompt the user to input username and password to login to Piazza"""
        while True:
            try:
                self._piazza.user_login()
                break
            except AuthenticationError:
                logger.error('Invalid Username/Password')
                continue
