import platform

import simplejson as json
from datetime import datetime, timedelta
import time
import os

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
import boto3
import pandas as pd
import numpy as np

from app.exception import InvalidUsage
from app.constants import POST_AGE_SIGMOID_OFFSET, POST_MAX_AGE_DAYS


def get_posts_table(course_id):
    dynamodb = boto3.resource('dynamodb')
    posts_table = dynamodb.Table(course_id)
    try:
        if posts_table.table_status == "ACTIVE":
            return posts_table
    except ClientError:
        return None


def get_courses_table():
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table('Courses')


def _validate_starting_time(starting_time):
    current_time = int(time.time())
    return True if (current_time > starting_time) else False


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


def get_inst_att_needed_posts(course_id, number_of_posts):
    """Retrieves the top instructor attention needed posts, for a specific
    course, with the search time being [starting_time, now). The following are
    the factors used in determining if a post warrants attention or not:

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
    filename = "".join(["/tmp/", course_id, ".json"])
    start = time.time()
    if os.path.exists(filename):
        with open(filename, "r") as json_file:
            filtered_posts = json.load(json_file)

        print("Retrieved {} Posts from /tmp in {} ms"
              .format(len(filtered_posts), (time.time() - start) * 1000))
    else:
        # Sanity check to see if the course_id sent is valid course_id or not
        posts = get_posts_table(course_id)
        if not posts:
            raise InvalidUsage('Invalid course id provided')

        DATE_CUTOFF = int(datetime.timestamp(datetime.now() + timedelta(days=-21)))

        try:
            start = time.time()
            response = posts.scan(
                FilterExpression=Attr("post_type").eq("question") &
                                 ~Attr("tags").contains("instructor-question") &
                                 Attr("created").gt(DATE_CUTOFF)
            )
            filtered_posts = response.get("Items")

            while 'LastEvaluatedKey' in response:
                response = posts.scan(
                    FilterExpression=Attr("post_type").eq("question") &
                                     ~Attr("tags").contains("instructor-question") &
                                     Attr("created").gt(DATE_CUTOFF),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                filtered_posts.extend(response['Items'])
        except ClientError as ce:
            print(ce)
            return []

        if "Linux" in platform.platform():
            with open(filename, "w") as json_file:
                json.dump(filtered_posts, json_file)

        print("Retrieved {} Posts from DDB in {} ms"
              .format(len(response), (time.time() - start) * 1000))

    def _create_top_post(post):
        post_data = {"title": post["subject"], "post_id": int(post["post_id"])}

        # properties includes [# unresolved followups, # views,
        #                      has_instructor_answer, has_student_answer, tags]
        properties = ["{} unresolved followups".format(post["num_unresolved_followups"]),
                      "{} views".format(post["num_views"])]

        if post.get("i_answer") is None:
            properties.append("No Instructor answers")
        if post.get("s_answer") is None:
            properties.append("No Student answers")
        if post.get("tags") is not None:
            properties.append("Tags - {}".format(", ".join(post["tags"])))

        post_data["properties"] = properties
        return post_data

    if len(filtered_posts) <= number_of_posts:
        return list(map(_create_top_post, filtered_posts))

    # Pick out posts with no instructor answer
    filtered_posts = [post for post in filtered_posts if post.get("i_answer") is None]
    # posts = posts.filter(i_answer=None)
    if len(filtered_posts) <= number_of_posts:
        return list(map(_create_top_post, filtered_posts))

    # Pick out posts with no instructor or student answer
    filtered_posts = [post for post in filtered_posts if post.get("s_answer") is None]
    # posts = posts.filter(s_answer=None)
    if len(filtered_posts) <= number_of_posts:
        return list(map(_create_top_post, filtered_posts))

    # Otherwise, return the n top posts sorted by number of unresolved followup
    # questions and views
    filtered_posts = sorted(filtered_posts, key=lambda a: (a.get('num_unresolved_followups'), a.get('num_views')))
    n_posts = min(len(filtered_posts), number_of_posts)
    return list(map(_create_top_post, filtered_posts[:n_posts]))


def get_stud_att_needed_posts(course_id, num_posts):
    """Retrieves the top student attention needed posts, for a specific course,
    with the search time being [starting_time, now). The posts from the past
    three days are sorted in the following order:

    1) Number of views
    2) Number of followups

    Finally, the top posts based on the age of the post are returned

    Parameters
    ----------
    course_id : str
        The course id of the class
    num_posts : int
        Number of posts that need to be returned

    Return
    ------
    top_posts : list
        A list of dictionary of posts
    """
    now = datetime.now()
    # Sanity check to see if the course_id sent is valid course_id or not
    filename = "".join(["/tmp/", course_id, ".json"])
    start = time.time()
    if os.path.exists(filename):
        with open(filename, "r") as json_file:
            filtered_posts = json.load(json_file)

        print("Retrieved {} Posts from /tmp in {} ms"
              .format(len(filtered_posts), (time.time() - start) * 1000))
    else:
        posts = get_posts_table(course_id)
        if not posts:
            raise InvalidUsage('Invalid course id provided')
        print("Checked if course was valid in {} ms"
              .format((time.time() - start) * 1000))

        max_age_date = int(datetime.timestamp(now - timedelta(hours=POST_MAX_AGE_DAYS * 24)))
        print(max_age_date)

        try:
            response = posts.scan(
                FilterExpression=Attr("post_type").eq("question") &
                                 ~Attr("tags").contains("instructor-question") &
                                 Attr("created").gt(max_age_date)
            )
            filtered_posts = response.get("Items")

            while 'LastEvaluatedKey' in response:
                response = posts.scan(
                    FilterExpression=Attr("post_type").eq("question") &
                                     ~Attr("tags").contains("instructor-question") &
                                     Attr("created").gt(max_age_date),
                    ExclusiveStartKey=response['LastEvaluatedKey'])
                filtered_posts.extend(response['Items'])
        except ClientError as ce:
            print(ce)
            return []

        if "Linux" in platform.platform():
            with open(filename, "w") as json_file:
                json.dump(filtered_posts, json_file)

        print("Retrieved {} Posts from DDB in {} ms"
              .format(len(filtered_posts), (time.time() - start) * 1000))

    if len(filtered_posts) == 0:
        print("No posts found since {} for course_id {}".format(max_age_date, course_id))
        return []

    def _create_top_post(post):
        post_data = {
            "post_id": int(post["post_id"]),
            "subject": post["subject"],
            "date_modified": int(post["created"]),
            "followups": len(post["followups"]),
            "views": int(post["num_views"]),
            "tags": post["tags"],
            "i_answer": True if post.get("i_answer") is not None else False,
            "s_answer": True if post.get("s_answer") is not None else False,
            "resolved": True if int(post.get("num_unresolved_followups")) == 0 else False
        }

        return post_data

    def _posts_bqs_to_df(bqs):
        dictionary = {
            'post_id': [int(post["post_id"]) for post in bqs],
            'created': [datetime.fromtimestamp(int(post["created"])) for post in bqs],
            'num_followups': [len(post["followups"]) for post in bqs],
            'num_views': [int(post["num_views"]) for post in bqs]
        }
        return pd.DataFrame.from_dict(dictionary)

    def _sigmoid(x, lookback, y_axis_flip=False):
        exponential = np.exp((-1) ** y_axis_flip) * (x - lookback)
        return exponential / (1 + exponential)

    def _min_max_norm(x):
        x = x + 1
        return x / (x.max() - x.min())

    print("{} filtered posts".format(len(filtered_posts)))
    start = time.time()
    posts_df = _posts_bqs_to_df(filtered_posts)
    posts_df.created = posts_df.created.fillna(posts_df.created.min())
    posts_age = (now - posts_df.created)
    posts_df['norm_created'] = _sigmoid(posts_age.dt.days,
                                        POST_AGE_SIGMOID_OFFSET, True)
    posts_df['norm_num_followups'] = _min_max_norm(posts_df.num_followups)
    posts_df['norm_num_views'] = _min_max_norm(posts_df.num_views)
    posts_df['importance'] = (posts_df.norm_created *
                              posts_df.norm_num_followups *
                              posts_df.norm_num_views)

    posts_df = posts_df.sort_values(by='importance', ascending=False)
    filtered_posts_ids = list(posts_df.head(num_posts).post_id)
    top_posts = [post for post in filtered_posts if post["post_id"] in filtered_posts_ids]
    retval = list(map(_create_top_post, top_posts))
    print("{} Recommended Posts in {} ms"
          .format(len(retval), (time.time() - start) * 1000))
    return retval
