import platform

import botocore
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
from app.utils import pretty_date


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def get_posts_table(course_id):
    dynamodb = boto3.resource("dynamodb")
    posts_table = dynamodb.Table(course_id)
    try:
        if posts_table.table_status == "ACTIVE":
            return posts_table
    except ClientError:
        return None


def get_courses_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table("Courses")


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
    return pd.DataFrame.from_dict(
        {
            "course_id": [event.event_data.course_id for event in bqs],
            "time": [event.time for event in bqs],
            "event": [event.event_name for event in bqs],
            "user_id": [event.user_id for event in bqs],
        }
    )


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

        print(
            "Retrieved {} Posts from /tmp in {} ms".format(
                len(filtered_posts), (time.time() - start) * 1000
            )
        )
    else:
        # Sanity check to see if the course_id sent is valid course_id or not
        posts = get_posts_table(course_id)
        if not posts:
            raise InvalidUsage("Invalid course id provided")

        try:
            start = time.time()
            response = posts.scan(
                FilterExpression=~Attr("tags").contains("instructor-question")
            )
            filtered_posts = response.get("Items")

            while "LastEvaluatedKey" in response:
                response = posts.scan(
                    FilterExpression=~Attr("tags").contains("instructor-question"),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                filtered_posts.extend(response["Items"])
        except ClientError as ce:
            print(ce)
            return []

        if "Linux" in platform.platform():
            with open(filename, "w") as json_file:
                json.dump(filtered_posts, json_file, cls=SetEncoder)

        print(
            "Retrieved {} Posts from DDB in {} ms".format(
                len(response), (time.time() - start) * 1000
            )
        )

    def _create_top_post(post):
        post_data = {
            "title": post["subject"],
            "post_id": int(post["post_id"]),
            "num_views": int(post["num_views"]),
            "num_updates": int(post.get("num_updates", 0)),
            "num_unresolved_followups": int(post.get("num_unresolved_followups", 0)),
            "i_answer": True if post.get("i_answer") else False,
            "s_answer": True if post.get("s_answer") else False,
            "tags": post.get("tags"),
            "last_modified": int(post.get("created")),
            "pretty_date": pretty_date(int(post.get("created"))),
            "assignees": list(post.get("assignees", [])),
            "good_questions": int(post.get("num_good_questions", 0)),
            "num_words": len(post.get("body", "").split()),
            "resolved": bool(post.get("resolved")) if post.get("resolved") else False,
        }

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
    filtered_posts = sorted(
        filtered_posts,
        key=lambda a: (a.get("num_unresolved_followups", 0), a.get("num_views", 0)),
    )
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
    filename = "".join(["/tmp/", course_id, ".json"])
    start = time.time()
    if os.path.exists(filename):
        with open(filename, "r") as json_file:
            recs = json.load(json_file)

        print(
            "Retrieved {} Posts from /tmp in {} ms".format(
                len(recs), (time.time() - start) * 1000
            )
        )
    else:
        try:
            boto3.client('s3').download_file("parqr", course_id + ".json", filename)
        except botocore.exceptions.ClientError as e:
            print("Could not find recs for cid '{}'".format(course_id))
            return []
        else:
            print("Downloaded recs from s3")
            with open(filename, "rb") as input_file:
                recs = json.load(input_file)

        print(
            "Retrieved {} Posts from s3 in {} ms".format(
                len(recs), (time.time() - start) * 1000
            )
        )

    return recs
