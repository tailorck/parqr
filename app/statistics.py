from datetime import datetime
import time
import logging

import pandas as pd

from app.models import Course, Event, Post
from app.exception import InvalidUsage


logger = logging.getLogger('app')


def is_course_id_valid(course_id):
    """A check to see if the course_id has parqr installed over it or not

    Parameters
    ----------
    course_id : str
        The course id of the class

    Return
    ------
    is_valid : bool
        True or False based on whether the course_id is valid or not
    """
    return False if not Course.objects(course_id=course_id) else True


def _validate_starting_time(starting_time):
    current_time = int(time.time())
    return True if (current_time > starting_time) else False


def get_unique_users(course_id, starting_time):
    """Retrieves the exact count of unique users in course that were active
    users of PARQR from the starting time specified to current time.

    Parameters
    ----------
    course_id : str
        The course id of the class for which unique users to be reported
    starting_time : int
        Time in microseconds. This specifies the initial time from where
        the unique active user count needs to be reported

    Return
    ------
    unique_active_user_count : int
        Count of unique users for the course_id in between starting time
        and current time (now).
    """

    # Sanity check to see if the course_id sent is valid course_id or not
    is_valid = is_course_id_valid(course_id)
    if not is_valid:
        raise InvalidUsage('Invalid course id provided')

    # Starting time must be an integer that is not more than the current
    # time. It should be in microseconds format.
    is_starting_time_valid = _validate_starting_time(starting_time)
    if not is_starting_time_valid:
        raise InvalidUsage('Invalid starting time provided')

    starting_date_time = datetime.fromtimestamp(starting_time)
    filtered_events = Event.objects.filter(event_data__course_id=course_id,
                                           time__gt=starting_date_time)
    unique_users = filtered_events.distinct('user_id')
    return len(unique_users)


def events_bqs_to_df(bqs):
    """
    Converts a mongo BaseQuerySet (the result of a filtered query) to a pandas
    dataframe

    :param bqs: BaseQuerySet to be converted
    :type bqs: flask_mongoengine.BaseQuerySet

    :return: dataframe whose rows are individual events
    """
    return pd.DataFrame.from_dict({
        'course_id': [event.event_data.course_id for event in bqs],
        'time': [event.time for event in bqs],
        'event': [event.event_name for event in bqs],
        'user_id': [event.user_id for event in bqs]
        })


def number_posts_prevented(course_id, starting_time):
    """Retrieves the exact number of new posts that parqr prevents.
       Without the actual knowledge of post_id at the time of writing a new post,
       the below calculations are an approximate.

    Parameters
    ----------
    course_id : str
        The course id of the class for which the number of prevented posts are
        to be reported
    starting_time : int
        Time in microseconds. This specifies the initial time from where
        the number of prevented posts are to be reported

    Return
    ------
    parqr_prevented_posts : int
        Number of prevented posts are to be reported for the course_id in between
        starting time and current time (now).
    """

    # Sanity check to see if the course_id sent is valid course_id or not
    is_valid = is_course_id_valid(course_id)
    if not is_valid:
        raise InvalidUsage('Invalid course id provided')

    # Starting time must be an integer that is not more than the current
    # time. It should be in microseconds format.
    is_starting_time_valid = _validate_starting_time(starting_time)
    if not is_starting_time_valid:
        raise InvalidUsage('Invalid start time provided')

    # Extract relevant information from mongoDB for the course_id
    starting_datetime = datetime.fromtimestamp(1000 * starting_time)
    events = Event.objects(event_data__course_id=course_id, 
                            time__gt=starting_datetime)
    events = events.order_by('user_id', 'time')

    events_df_course_id_sorted = events_bqs_to_df(events)

    # There may be possible duplicate entries in the database with same events
    # being logged in a continuous format. This is not a logging issue, but arises
    # due to various reasons.
    # 1. Squash duplicate events in the dataframe and keep only one instance of
    # each
    df_for_posts_prevented = events_df_course_id_sorted \
        .loc[events_df_course_id_sorted['event'] != events_df_course_id_sorted
        .shift()['event']]

    # 1. Filter df by 'newPost' event and create a new df
    # 2. Group by user_id to identify individual's activity on piazza
    df_posts_prevented_new_post = df_for_posts_prevented \
        .loc[df_for_posts_prevented['event'] == 'newPost'] \
        .groupby('user_id')['event'].size().to_frame().reset_index()

    # 1. Filter df by 'postSubmitted' event and create a new df
    # 2. Group by user_id to identify individual's activity on piazza
    df_posts_prevented_post_submitted = df_for_posts_prevented \
        .loc[df_for_posts_prevented['event'] == 'postSubmitted'] \
        .groupby('user_id')['event'].size().to_frame().reset_index()

    df_posts_prevented_new_post.rename(columns={'event': 'newPost'},
                                       inplace=True)

    df_posts_prevented_post_submitted.rename(columns={'event': 'postSubmitted'},
                                             inplace=True)

    df_posts_prevented_new_post.set_index('user_id', inplace=True)
    df_posts_prevented_post_submitted.set_index('user_id', inplace=True)
    df_final = df_posts_prevented_new_post \
        .join(df_posts_prevented_post_submitted['postSubmitted'])

    df_final = df_final.fillna(0)

    df_final['parqr_wins'] = df_final['newPost'] - df_final['postSubmitted']
    df_final.loc[df_final['parqr_wins'] < 0] = 0

    sum_row = df_final.sum(axis=0)
    parqr_prevented_posts = sum_row['parqr_wins']

    return int(parqr_prevented_posts)


def total_posts_in_course(course_id):
    """Retrieves the exact count of total posts made for a particular
    course_id from the starting time specified to current time.

    Parameters
    ----------
    course_id : str
        The course id of the class

    Return
    ------
    total_posts_course : int
        Count of total posts for the course_id in between starting time
        and current time (now).
    """

    # Sanity check to see if the course_id sent is valid course_id or not
    is_valid = is_course_id_valid(course_id)
    if not is_valid:
        raise InvalidUsage('Invalid course id provided')

    return Post.objects(course_id=course_id).count()


def get_top_attention_warranted_posts(course_id, number_of_posts):
    """Retrieves the top posts for a specific tag, for a specific course,
    with the search time being [starting_time, now). The following are the
    factors used in determining if a post warrants attention or not:
    1) There is no Instructor answer for it
    2) There is no student answer for it
    3) There are unanswered followup questions for the post

    Finally, the top posts based on the age of the post are returned

    Parameters
    ----------
    course_id : str
        The course id of the class
    number_of_posts : int
        Number of posts that need to be returned

    Return
    ------
    top_posts : list
        A list of dictionary of posts
    """

    # Sanity check to see if the course_id sent is valid course_id or not
    is_valid = is_course_id_valid(course_id)
    if not is_valid:
        raise InvalidUsage('Invalid course id provided')

    posts = Post.objects(course_id=course_id, post_type='question',
                         tags__nin=['instructor-question'])

    def _create_top_post(post):
        post_data = {}
        post_data["title"] = post.subject
        post_data["post_id"] = post.post_id

        # properties includes [# unresolved followups, # views, 
        #                      has_instructor_answer, has_student_answer, tags]
        properties = ["{} unresolved followups".format(post.num_unresolved_followups), 
                      "{} views".format(post.num_views)]

        if not post.i_answer:
            properties.append("No Instructor answers")
        if not post.s_answer:
            properties.append("No Student answers")
        if post.tags:
            properties.append("Tags - {}".format(", ".join(post.tags)))

        post_data["properties"] = properties
        return post_data

    if posts.count() <= number_of_posts:
        return map(_create_top_post, posts)

    # Pick out posts with no instructor answer
    posts = posts.filter(i_answer=None)
    if posts.count() <= number_of_posts:
        return map(_create_top_post, posts)

    # Pick out posts with no instructor or student answer
    posts = posts.filter(s_answer=None)
    if posts.count() <= number_of_posts:
        return map(_create_top_post, posts)

    # Otherwise, return the n top posts sorted by number of unresolved followup
    # questions and views
    posts = posts.order_by('-num_unresolved_followups', '-num_views')
    n_posts = min(posts.count(), number_of_posts)
    return map(_create_top_post, posts[:n_posts])
