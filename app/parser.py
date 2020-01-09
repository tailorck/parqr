from datetime import datetime
import time
import logging

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError
from progressbar import ProgressBar

from app.constants import DATETIME_FORMAT
from app.models.course import Course
from app.models.post import Post

from app.utils import read_credentials, stringify_followups

logger = logging.getLogger('app')


class Parser(object):
    def __init__(self):
        """Initialize the Piazza object and login with the encrypted username
        and password
        """
        self._piazza = Piazza()
        self._login()
        self.limit = 1000

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
        except KeyError:
            logger.error('Unable to get valid statistics for course_id: {}'
                         .format(course_id))
            return False

        # Get handle to the corresponding course document or create a new one
        course = Course.objects(course_id=course_id)
        if not course:
            enrolled_courses = self._piazza.get_user_classes()
            for enrolled_course in enrolled_courses:
                if enrolled_course["nid"] == course_id:
                    course_name = enrolled_course["name"]
                    course_number = enrolled_course["num"]
                    course_term = enrolled_course["term"]

                    Course(course_id=course_id,
                           course_name=course_name,
                           course_number=course_number,
                           course_term=course_term).save()

        pids_to_update = []
        current_pids = set()
        for offset in range(0, total_questions, self.limit):
            feed = network.get_feed(limit=self.limit, offset=offset)
            for post in feed['feed']:
                if post['status'] == 'deleted' or post['status'] == 'private':
                    continue

                pid = post['nr']
                new_modified = datetime.strptime(post['modified'], DATETIME_FORMAT)

                # If the post is neither deleted nor private, it should be in the db
                current_pids.add(pid)

                db_post = Post.objects(course_id=course_id, post_id=pid).first()
                if not db_post or db_post.modified < new_modified:
                    pids_to_update.append(pid)

        pbar = ProgressBar(maxval=len(pids_to_update))
        logger.info("Parsing {} posts".format(len(pids_to_update)))
        start_time = time.time()
        for pid in pbar(pids_to_update):
            # Get the post if available
            post = network.get_post(pid)

            # TODO: Parse the type of the post, to indicate if the post is
            # a note/announcement

            # Extract the subject, body, and tags from post
            subject, body, tags, post_type = self._extract_question_details(post)

            # Extract number of unique views of the post
            num_views = post['unique_views']

            # Get creation time and last modified time
            created = datetime.strptime(post['created'], DATETIME_FORMAT)
            modified = datetime.strptime(post['change_log'][-1]['when'], DATETIME_FORMAT)

            # Extract number of unresolved followups (if any)
            num_unresolved_followups = self._extract_num_unresolved(post)

            # Extract the student and instructor answers if applicable
            s_answer, i_answer = self._extract_answers(post)

            # Extract the followups and feedbacks if applicable
            followups = self._extract_followups(post)

            # If post exists, check if it has been updated and update db if
            # necessary. Else, insert new post and add to course's post list
            Post.objects(course_id=course_id, post_id=pid).modify(upsert=True, new=True,
                                                                  set__course_id=course_id,
                                                                  set__created=created,
                                                                  set__modified=modified,
                                                                  set__post_id=pid,
                                                                  set__subject=subject,
                                                                  set__body=body,
                                                                  set__tags=tags,
                                                                  set__post_type=post_type,
                                                                  set__s_answer=s_answer,
                                                                  set__i_answer=i_answer,
                                                                  set__followups=followups,
                                                                  set__num_unresolved_followups=num_unresolved_followups,
                                                                  set__num_views=num_views)

        # self._delete_privated_posts(course_id, current_pids)

        # TODO: Figure out another way to verify whether the current user has access to a class.
        # In the event the course_id was invalid or no posts were parsed, delete course object
        if Post.objects(course_id=course_id).count() == 0:
            logger.error('Unable to parse posts for course: {}. Please '
                         'confirm that the piazza user has access to this '
                         'course'.format(course_id))
            Course.objects(course_id=course_id).delete()
            return False

        end_time = time.time()
        time_elapsed = end_time - start_time
        logger.info('Course updated. {} posts scraped in: {:.2f}s'.format(len(pids_to_update), time_elapsed))

        return True

    def _delete_privated_posts(self, course_id, current_pids):
        # Get all the posts for this course in the db
        db_pids = set(Post.objects(course_id=course_id).distinct(field='post_id'))

        # Delete pids which are in the db but aren't one of the current pids
        pids_to_delete = db_pids - current_pids
        deleted_posts = Post.objects(post_id__in=pids_to_delete).delete()

        if deleted_posts > 0:
            logger.info("Deleted {} posts while parsing course_id {} ".format(deleted_posts, course_id))

    def _check_for_updates(self, curr_post, new_fields):
        """Checks if post has been updated since last scrape.

        Parameters
        ----------
        curr_post : app.models.post
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

        checks = [
            curr_post.subject != new_fields['subject'],
            curr_post.body != new_fields['body'],
            curr_post.s_answer != new_fields['s_answer'],
            curr_post.i_answer != new_fields['i_answer'],
            curr_followups_str != new_followups_str,
            curr_post.num_views != new_fields['num_views'],
            curr_post.num_unresolved_followups != new_fields['num_unresolved_followups'],
            curr_post.tags != new_fields['tags'],
            curr_post.post_type != new_fields['post_type'],
        ]
        return any(checks)

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
        tags = post['tags']
        post_type = post['type']
        return subject, parsed_body, tags, post_type

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
        except (UnicodeDecodeError, AuthenticationError) as e:
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
