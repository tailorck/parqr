from datetime import datetime, timedelta
import time
import base64

import boto3
import numpy as np
import pandas as pd
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
import json

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError

from app.constants import POST_MAX_AGE_DAYS, POST_AGE_SIGMOID_OFFSET
from app.exception import InvalidUsage
from app.utils import pretty_date

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
dynamodb = boto3.client("dynamodb")
dynamodb_resource = boto3.resource("dynamodb")


def get_secret(secret_name):
    region_name = "us-east-2"

    # Create a Secrets Manager client
    client = boto3.client(service_name="secretsmanager", region_name=region_name)

    response = client.get_secret_value(SecretId=secret_name)

    return json.loads(response["SecretString"])


def get_course_table(course_id):
    dynamodb = boto3.client("dynamodb")
    try:
        # Check if course table exists
        dynamodb.describe_table(TableName=course_id)
    except ClientError as ce:
        if ce.response.get("Error").get("Code") == "ResourceNotFoundException":
            # If course table doesn't exist, make a new table
            dynamodb.create_table(
                TableName=course_id,
                KeySchema=[{"AttributeName": "post_id", "KeyType": "HASH", }],
                AttributeDefinitions=[
                    {"AttributeName": "post_id", "AttributeType": "N", }
                ],
                ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            )
            print("Creating new table for course {}".format(course_id))
        else:
            raise ce

    course_table = boto3.resource("dynamodb").Table(course_id)
    course_table.wait_until_exists()
    return course_table


def update_student_recs(course_id, num_posts=5):
    posts = get_course_table(course_id)
    if not posts:
        raise InvalidUsage("Invalid course id provided")

    now = datetime.now()
    max_age_date = int(
        datetime.timestamp(now - timedelta(hours=POST_MAX_AGE_DAYS * 24))
    )
    print(max_age_date)

    start = time.time()
    try:
        response = posts.scan(
            FilterExpression=Attr("post_type").eq("question")
                             & ~Attr("tags").contains("instructor-question")
                             & Attr("created").gt(max_age_date)
        )
        filtered_posts = response.get("Items")

        while "LastEvaluatedKey" in response:
            response = posts.scan(
                FilterExpression=Attr("post_type").eq("question")
                                 & ~Attr("tags").contains("instructor-question")
                                 & Attr("created").gt(max_age_date),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            filtered_posts.extend(response["Items"])
    except ClientError as ce:
        print(ce)
        return []

    print(
        "Retrieved {} Posts from DDB in {} ms".format(
            len(filtered_posts), (time.time() - start) * 1000
        )
    )

    if len(filtered_posts) == 0:
        print(
            "No posts found since {} for course_id {}".format(max_age_date, course_id)
        )
        return []

    def _create_top_post(post):
        post_data = {
            "post_id": int(post["post_id"]),
            "subject": post["subject"],
            "date_modified": int(post["created"]),
            "followups": len(post.get("followups", [])),
            "views": int(post["num_views"]),
            "tags": post["tags"],
            "pretty_date": pretty_date(int(post.get("created"))),
            "i_answer": True if post.get("i_answer") is not None else False,
            "s_answer": True if post.get("s_answer") is not None else False,
            "resolved": True if int(post.get("num_unresolved_followups", 0)) == 0 else False,
        }

        return post_data

    def _posts_bqs_to_df(bqs):
        dictionary = {
            "post_id": [int(post["post_id"]) for post in bqs],
            "created": [datetime.fromtimestamp(int(post["created"])) for post in bqs],
            "num_followups": [len(post.get("followups", [])) for post in bqs],
            "num_views": [int(post["num_views"]) for post in bqs],
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
    posts_age = now - posts_df.created
    posts_df["norm_created"] = _sigmoid(
        posts_age.dt.days, POST_AGE_SIGMOID_OFFSET, True
    )
    posts_df["norm_num_followups"] = _min_max_norm(posts_df.num_followups)
    posts_df["norm_num_views"] = _min_max_norm(posts_df.num_views)
    posts_df["importance"] = (
            posts_df.norm_created * posts_df.norm_num_followups * posts_df.norm_num_views
    )

    posts_df = posts_df.sort_values(by="importance", ascending=False)
    filtered_posts_ids = list(posts_df.head(num_posts).post_id)
    top_posts = [
        post for post in filtered_posts if post["post_id"] in filtered_posts_ids
    ]
    retval = list(map(_create_top_post, top_posts))
    print(
        "{} Recommended Posts in {} ms".format(
            len(retval), (time.time() - start) * 1000
        )
    )

    s3 = get_boto3_s3()

    s3.put_object(
        Bucket='parqr',
        Key='{}.json'.format(course_id),
        Body=bytes(json.dumps(retval), encoding='utf8')
    )


def get_num_updates(post, network):
    # Search through log to see how many updates there have been
    # since the most recent professor/ta post
    counter = 0
    if not post.get("change_log"):
        print("No log for post {}".format(post.get("nr")))
        return 0
    for entry in post["change_log"][::-1]:
        user = entry.get("uid", "anon")
        if user != "anon":
            role = network.get_users([user])[0].get("role")
        else:
            role = "anon"
        if role not in ["professor", "ta"]:
            counter += 1
        else:
            break
    return counter


def get_boto3_s3():
    return boto3.client('s3')


class Parser(object):
    def __init__(self):
        """Initialize the Piazza object and login with the encrypted username
        and password
        """
        self._piazza = Piazza()
        self._login()

    def _login(self):
        """Try to read the login file else prompt the user for manual login"""
        try:
            parqr_credentials = get_secret("piazza_credentials")
            email = parqr_credentials.get("piazza_username")
            password = parqr_credentials.get("piazza_password")
            self._piazza.user_login(email, password)
        except (UnicodeDecodeError, AuthenticationError) as e:
            print("Unable to authenticate with Piazza. Incorrect Email/Password")

    def get_enrolled_courses(self):
        """Returns currently enrolled courses in a pretty format method"""
        enrolled_courses = self._piazza.get_user_classes()
        return [
            {
                "name": d["name"],
                "course_id": d["nid"],
                "term": d["term"],
                "course_num": d["num"],
            }
            for d in enrolled_courses
        ]

    def get_stats_for_enrolled_courses(self):
        enrolled_courses = self.get_enrolled_courses()
        courses = dynamodb_resource.Table("Courses")
        for course in enrolled_courses:
            stats = courses.get_item(Key={"course_id": course.get("course_id")}).get(
                "Item"
            )
            if stats:
                course["stats"] = {}
                course["stats"]["num_posts"] = stats.get("num_posts")
                course["stats"]["num_students"] = stats.get("num_students")
                course["stats"]["num_parqr_users"] = len(stats.get("parqr_users", []))

        s3 = get_boto3_s3()

        s3.put_object(
            Bucket='parqr',
            Key='courses.json',
            Body=bytes(json.dumps(enrolled_courses), encoding='utf8')
        )
        return enrolled_courses

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
        print("Parsing posts for course: {}".format(course_id))
        network = self._piazza.network(course_id)
        train = False

        courses = dynamodb_resource.Table("Courses")
        course_info = courses.update_item(
            Key={"course_id": course_id}, ReturnValues="ALL_OLD"
        ).get("Attributes")

        if course_info is None or course_info.get("last_modified") is None:
            last_modified = 0
        else:
            last_modified = int(course_info.get("last_modified"))
            if last_modified > datetime.now().timestamp():
                last_modified = last_modified / 1000

        if course_info is None or course_info.get("all_pids") is None:
            previous_all_pids = set()
        else:
            previous_all_pids = set([int(i) for i in course_info.get("all_pids")])

        try:
            feed = network.get_feed(limit=99999)["feed"]
            all_pids = set([post["nr"] for post in feed])
            pids = [
                post["nr"]
                for post in feed
                if datetime.strptime(post["modified"], DATETIME_FORMAT).timestamp()
                   > last_modified
            ]
        except KeyError:
            print("Unable to get feed for course_id: {}".format(course_id))
            return False, None

        posts = get_course_table(course_id)

        current_pids = set()
        start_time = time.time()
        for pid in pids:
            # Get the post if available
            try:
                post = network.get_post(pid)
            except RequestError:
                all_pids.discard(pid)
                continue

            # Skip deleted and private posts
            if post["status"] == "deleted" or post["status"] == "private":
                if pid in previous_all_pids:
                    print(
                        "Deleted post with pid {} and course id {} from Posts".format(
                            pid, course_id
                        )
                    )
                    all_pids.discard(pid)
                    previous_all_pids.discard(pid)
                    posts.delete_item(
                        Key={"post_id": pid}
                    )
                continue

            # If the post is neither deleted nor private, it should be in the db
            current_pids.add(pid)

            # TODO: Parse the type of the post, to indicate if the post is
            # a note/announcement

            # Extract the subject, body, and tags from post
            subject, body, tags, post_type = self._extract_question_details(post)

            # Extract number of unique views of the post
            num_views = post["unique_views"]

            # Get creation and last modified time
            created = datetime.strptime(post["created"], DATETIME_FORMAT)
            # Extract number of unresolved followups (if any)
            num_unresolved_followups = self._extract_num_unresolved(post)

            # Extract the student and instructor answers if applicable
            s_answer, i_answer = self._extract_answers(post)

            # Extract the student and instructor answer metadata
            (
                s_answer_created,
                i_answer_created,
                s_answer_uid,
                i_answer_uid,
            ) = self._extract_answer_metadata(post)

            # Extract the followups and feedbacks if applicable
            followups = self._extract_followups(post)

            # insert post and add to course's post list
            item = {
                "created": int(created.timestamp()),
                "subject": subject,
                "body": body,
                "tags": tags,
                "post_type": post_type,
                "s_answer": s_answer,
                "s_answer_created": s_answer_created,
                "s_answer_uid": s_answer_uid,
                "i_answer": i_answer,
                "i_answer_created": i_answer_created,
                "i_answer_uid": i_answer_uid,
                "followups": followups,
                "num_unresolved_followups": num_unresolved_followups,
                "num_views": num_views,
                "num_updates": get_num_updates(post, network),
                "num_good_questions": post.get("gd", 0),
                "resolved": True if num_unresolved_followups == 0 and (s_answer or i_answer) else False,
            }
            cleaned_item = {k: v for k, v in item.items() if v}
            update_expression = "SET " + ", ".join([" = :".join([key, key]) for key in cleaned_item.keys()])
            attribute_values = {}
            for k, v in cleaned_item.items():
                attribute_values[":" + k] = v
            try:
                posts.update_item(
                    Key={
                        "post_id": pid,
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=attribute_values
                )
                train = True
            except ClientError as e:
                print(pid, cleaned_item)
                print(e)
                current_pids.discard(pid)
                all_pids.discard(pid)
                continue

        deleted_pids = previous_all_pids - all_pids
        for pid in deleted_pids:
            all_pids.discard(pid)
            print(
                "Deleted post with pid {} and course id {} from Posts".format(
                    pid, course_id
                )
            )
            posts.delete_item(
                Key={"post_id": pid, }
            )
            train = True

        # TODO: Figure out another way to verify whether the current user has access to a class.
        # In the event the course_id was invalid or no posts were parsed, delete course object
        # TODO: Should we delete the table?
        if len(pids) != 0 and len(current_pids) == 0:
            print(
                "Unable to parse posts for course: {}. Please "
                "confirm that the piazza user has access to this "
                "course".format(course_id)
            )
            return False, None
        end_time = time.time()
        time_elapsed = end_time - start_time
        print(
            "Course updated. {} new posts scraped in: {:.2f}s".format(
                len(current_pids), time_elapsed
            )
        )

        try:
            all_users = str(len(network.get_all_users()))
        except RequestError:
            all_users = "N/A"

        courses.update_item(
            Key={"course_id": course_id},
            UpdateExpression="SET #pids = :pids, num_students = :num_students, "
                             "num_posts = :num_posts, last_modified = :last_modified",
            ExpressionAttributeNames={"#pids": "all_pids"},
            ExpressionAttributeValues={
                ":pids": all_pids,
                ":num_students": all_users,
                ":num_posts": str(network.get_statistics()["total"]["questions"]),
                ":last_modified": int(datetime.now().timestamp()),
            },
        )

        return True, train

    def _extract_num_unresolved(self, post):
        if len(post["children"]) > 0:
            unresolved_list = [
                post["children"][i]["no_answer"]
                for i in range(len(post["children"]))
                if post["children"][i]["type"] == "followup"
            ]
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
        subject = post["history"][0]["subject"]
        html_body = post["history"][0]["content"]
        parsed_body = BeautifulSoup(html_body, "html.parser").get_text()
        if parsed_body == "":
            parsed_body = None
        tags = post["tags"]
        post_type = post["type"]
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
        for response in post["children"]:
            if response["type"] == "s_answer":
                html_text = response["history"][0]["content"]
                s_answer = BeautifulSoup(html_text, "html.parser").get_text()
            elif response["type"] == "i_answer":
                html_text = response["history"][0]["content"]
                i_answer = BeautifulSoup(html_text, "html.parser").get_text()

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
        for child in post["children"]:

            data = {}
            if child["type"] == "followup":
                html_text = child["subject"]
                soup = BeautifulSoup(html_text, "html.parser")
                text = soup.get_text()
                if text:
                    data["text"] = text

                responses = []
                if child["children"]:
                    for activity in child["children"]:
                        html_text = activity["subject"]
                        soup = BeautifulSoup(html_text, "html.parser")
                        text = soup.get_text()
                        if text:
                            responses.append(text)

                    data["responses"] = responses

                followups.append(data)

        return followups

    def _extract_answer_metadata(self, post):
        """ Retrieves the metadata of the post's answer. I.e when was it answered? By whom?
        Note this currently doesn't consider any updates made to the answers

        Parameters
        ----------
        post : dict
            An object including the post information retrieved from a
            piazza_api call

        Returns
        -------
        s_answer_created : datetime or None
           timestamp in the changelog corresponding to when the student answer was posted
           or None if it doesn't exist
        i_answer_created : datetime or None
           timestamp in the changelog corresponding to when the instructor answer was posted
           or None if it doesn't exist
        s_answer_uid : str or None
           uid corresponding to the student answerer, or None if the answer doesn't exist or is anonymous
        i_answer_uid : str or None
           uid corresponding to the instructor answerer, or None if the answer doesn't exist
        """
        # TODO where do you want this constant?
        s_answer_created = None
        i_answer_created = None
        s_answer_uid = None
        i_answer_uid = None

        for change in post["change_log"]:
            if change["type"] == "i_answer":
                i_answer_created = int(datetime.strptime(change["when"], DATETIME_FORMAT).timestamp())
                i_answer_uid = change.get("uid")
            elif change["type"] == "s_answer":
                s_answer_created = int(datetime.strptime(change["when"], DATETIME_FORMAT).timestamp())
                s_answer_uid = change.get("uid")

        return s_answer_created, i_answer_created, s_answer_uid, i_answer_uid


def lambda_handler(event, context):
    print("Event: {}".format(event))
    print("Context: {}".format(context))
    if event.get("source") == "aws.events":
        course_id = event.get("resources")[0].split("/")[1]
    elif event.get("source") == "parqr-api":
        parser = Parser()
        return parser.get_stats_for_enrolled_courses()
    else:
        course_id = event["course_id"]
    print("Course ID: {}".format(course_id))
    update_student_recs(course_id)

    parser = Parser()
    parser.get_stats_for_enrolled_courses()
    success, train = parser.update_posts(course_id)
    if success:
        print("Successfully parsed")
        if train:
            print("Sending posts to ModelTrain")
            lambda_client = boto3.client("lambda")
            payload = {"course_ids": [course_id]}
            lambda_client.invoke(
                FunctionName="Parqr-ModelTrain:PROD",
                InvocationType="Event",
                Payload=bytes(json.dumps(payload), encoding="utf8"),
            )
    else:
        print("Error parsing")
