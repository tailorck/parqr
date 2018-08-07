from datetime import datetime
import time
import logging

from pymongo import MongoClient
import pandas as pd
import numpy as np
import delorean

from app.models import Course, Event, Post
from app.exception import InvalidUsage


logger = logging.getLogger('app')


def convert_db_posts_to_df():
    """This function converts the db.parqr.post collection into a dataframe,
    allowing faster calculations for the stats module

    Sample posts_df schema is as below

    {
        _id: bson.objectid.ObjectId,
        post_id: np.int64,
        course_id: unicode,
        subject: unicode,
        body: unicode,
        tags: list,
        s_answer: unicode,
        i_answer: unicode,
        followups: list(dict),
        num_unresolved_followups: int,
        num_views: int
    }

    Return
    ------
    posts_df : Dataframe with nine columns
        An posts dataframe which has all the information stored as part of
        the 'post' collention in mongo database.

    """

    # Step 1.
    # Make a connection to the Mongo Database using pymongo
    connection = MongoClient()

    # Step 2.
    # Get the required database. To Do - If not hardcode 'parqr', then what ?
    database = connection.parqr

    # Step 3.
    # Get the required collection. To Do - If not hardcode 'event', then what ?
    collection = database.post

    # Step 4.
    # Convert the entire collection into pandas dataframe with column names as
    # the mongo database
    posts_df = pd.DataFrame(list(collection.find()))
    return posts_df


def convert_db_course_to_df():
    """This function converts the db.parqr.course collection into a dataframe,
    allowing faster calculations for the stats module

    Sample course_df schema is as below

    {
        _id: bson.objectid.ObjectId,
        course_id: unicode,
        posts: bson.objectid.ObjectId
    }

    Return
    ------
    course_df : Dataframe with three columns
        An posts dataframe which has all the information stored as part of
        the 'post' collention in mongo database.

    """

    # Step 1.
    # Make a connection to the Mongo Database using pymongo
    connection = MongoClient()

    # Step 2.
    # Get the required database. To Do - If not hardcode 'parqr', then what ?
    database = connection.parqr

    # Step 3.
    # Get the required collection. To Do - If not hardcode 'event', then what ?
    collection = database.course

    # Step 4.
    # Convert the entire collection into pandas dataframe with column names as
    # the mongo database
    course_df = pd.DataFrame(list(collection.find()))
    return course_df


def convert_events_to_df():
    """This function converts the db.event collection into a dataframe,
    allowing faster calculations for the stats module

    Sample events_df schema is as below

    {
        _id: bson.objectid.ObjectId,
        event_data: dict(list(course_ids)),
        event_name: unicode,
        event_type: unicode,
        time: pandas._libs.tslib.Timestamp,
        user_id: unicode
    )

    Return
    ------
    events_df : Dataframe with four columns
        An events dataframe which has all the information stored as part of
        the 'event' collention in mongo database.

    """

    # Step 1.
    # Make a connection to the Mongo Database using pymongo
    connection = MongoClient()

    # Step 2.
    # Get the required database. To Do - If not hardcode 'parqr', then what ?
    database = connection.parqr

    # Step 3.
    # Get the required collection. To Do - If not hardcode 'event', then what ?
    collection = database.event

    # Step 4.
    # Convert the entire collection into pandas dataframe with column names as
    # the mongo database
    events_df = pd.DataFrame(list(collection.find()))

    feature_list = ['course_id', 'time', 'event', 'user_id']
    df = pd.DataFrame(0, index=np.arange(events_df.shape[0]), columns=feature_list)

    for i in range(events_df.shape[0]):
        df.loc[i, 'course_id'] = events_df.loc[i, 'event_data']['course_id']
        time_since_epoch = delorean.Delorean(events_df.loc[i, 'time'], timezone="UTC").epoch
        df.loc[i, 'time'] = time_since_epoch
        df.loc[i, 'event'] = events_df.loc[i, 'event_name']
        df.loc[i, 'user_id'] = events_df.loc[i, 'user_id']

    return df


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
    events_df = convert_events_to_df()

    # 1. Filter events_df based on course_id and starting time
    # 2. Reset Indexes of the resulting dataframe
    events_df_course_id = events_df.loc[(events_df['course_id'] == course_id) &
                                        (events_df['time'] / 1000 > starting_time),
                                        ['course_id', 'time', 'event', 'user_id']] \
                                   .reset_index(drop=True)

    # 1. Sort in ascending order by columns - user_id and time
    events_df_course_id_sorted = events_df_course_id.sort_values(by=['user_id',
                                                                     'time'],
                                                                 ascending=[True, True]).reset_index(drop=True)

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


def _create_top_posts(posts_df,
                      has_instructor_answer,
                      has_student_answer,
                      number_of_posts):
    # Reset index of the dataframe passed. This will help in
    # iterating over its indexes
    posts_df = posts_df.reset_index()

    top_n_posts = []

    for i in range(number_of_posts):
        # Dictionary to store data for each of the posts returned
        # Keys of the dictionary:
        # a) title
        # b) post_id
        # c) properties
        warranted_posts = {}

        # List of strings to store different properties of the post. Properties
        # include -
        # a) Number of unresolved followups
        # b) Number of views on the post'
        # c) Is instructor answer to the post present
        # d) Is student answer to the post present
        # e) Tags of the post
        property_of_a_single_post = []

        # Set value for title key
        warranted_posts["title"] = posts_df.loc[i]["subject"]

        # Set value for post_id key
        warranted_posts["post_id"] = posts_df.loc[i]["post_id"]

        # Create the properties list to be put into the list
        string_instructor_answer = "No Instructor answers"
        string_student_answer = "No Student answers"
        string_tags = "Tags - " + str(", ".join(posts_df.loc[i]["tags"]))
        string_num_views = str(int(posts_df.loc[i]["num_views"])) + " views"
        string_unresolved_followup = str(int(posts_df.loc[i]["num_unresolved_followups"])) \
                                     + " unresolved followups"

        property_of_a_single_post.append(string_unresolved_followup)
        property_of_a_single_post.append(string_num_views)

        if has_instructor_answer:
            property_of_a_single_post.append(string_instructor_answer)
        if has_student_answer:
            property_of_a_single_post.append(string_student_answer)
        if posts_df.loc[i]["tags"]:
            property_of_a_single_post.append(string_tags)

        # Set value for the properties key
        warranted_posts["properties"] = property_of_a_single_post

        # Append the dictionary into a list of top posts which need
        # attention
        top_n_posts.append(warranted_posts)

    return top_n_posts


def get_top_attention_warranted_posts(course_id,
                                      number_of_posts):
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

    # Extract the whole posts collection in mongo database into a dataframe
    posts_df = convert_db_posts_to_df()

    posts_df = posts_df.loc[posts_df['course_id'] == course_id]

    # Order of things to do:
    # 1) Remove all posts which are tagged as announcements
    posts_df_no_ann = posts_df[posts_df['tags'].apply(
        lambda x: 'announcements' not in x)]

    # 2) Pick out posts with no instructor answer
    posts_df_no_ann_i_null = posts_df_no_ann[posts_df_no_ann['i_answer'].isnull()]

    # Check if the number of posts remaining in posts_df_no_ann_i_null is
    # less than the number of posts to return
    if posts_df_no_ann_i_null.shape[0] <= number_of_posts:
        number_of_posts = posts_df_no_ann_i_null.shape[0]
        top_n_posts = _create_top_posts(posts_df_no_ann_i_null, 1, 0,
                                        number_of_posts)
        return top_n_posts

    # 3) Pick out posts with no student answers
    posts_df_no_ann_i_s_null = posts_df_no_ann_i_null[ \
        posts_df_no_ann_i_null['s_answer'].isnull()]

    if posts_df_no_ann_i_s_null.shape[0] <= number_of_posts:
        number_of_posts = posts_df_no_ann_i_s_null.shape[0]
        top_n_posts = _create_top_posts(posts_df_no_ann_i_s_null, 1, 1,
                                        number_of_posts)
        return top_n_posts

    # 4) Sort the dataframe by descending order of number of unresolved
    #    followup questions and number of views on the post
    posts_top_att_warr = posts_df_no_ann_i_s_null.sort_values(
        by=['num_unresolved_followups', 'num_views'],
        ascending=[False, False])

    number_of_posts = min(posts_top_att_warr.shape[0], number_of_posts)

    top_n_posts = _create_top_posts(posts_top_att_warr, 1, 1,
                                    number_of_posts)
    return top_n_posts
