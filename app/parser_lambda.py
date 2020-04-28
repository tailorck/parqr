from datetime import datetime
import time
import base64

import boto3
from botocore.exceptions import ClientError
import json

from bs4 import BeautifulSoup
from piazza_api import Piazza
from piazza_api.exceptions import AuthenticationError, RequestError

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
dynamodb = boto3.client('dynamodb')
dynamodb_resource = boto3.resource('dynamodb')


def get_secret(secret_name):
    region_name = "us-east-2"

    # Create a Secrets Manager client
    client = boto3.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    response = client.get_secret_value(
        SecretId=secret_name
    )

    return json.loads(response["SecretString"])


def get_course_table(course_id):
    dynamodb = boto3.client("dynamodb")
    try:
        # Check if course table exists
        dynamodb.describe_table(
            TableName=course_id
        )
    except ClientError as ce:
        if ce.response.get('Error').get('Code') == 'ResourceNotFoundException':
            # If course table doesn't exist, make a new table
            dynamodb.create_table(
                TableName=course_id,
                KeySchema=[
                    {
                        'AttributeName': 'post_id',
                        'KeyType': 'HASH',
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'post_id',
                        'AttributeType': 'N',
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                },
            )
            print("Creating new table for course {}".format(course_id))
        else:
            raise ce

    course_table = boto3.resource("dynamodb").Table(course_id)
    course_table.wait_until_exists()
    return course_table


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
            parqr_credentials = get_secret('piazza_credentials')
            email = parqr_credentials.get('piazza_username')
            password = parqr_credentials.get('piazza_password')
            self._piazza.user_login(email, password)
        except (UnicodeDecodeError, AuthenticationError) as e:
            print("Unable to authenticate with Piazza. Incorrect Email/Password")

    def get_enrolled_courses(self):
        """Returns currently enrolled courses in a pretty format method"""
        enrolled_courses = self._piazza.get_user_classes()
        return [{'name': d['name'], 'course_id': d['nid'], 'term': d['term'],
                 'course_num': d['num']} for d in enrolled_courses]

    def get_stats_for_enrolled_courses(self):
        enrolled_courses = self.get_enrolled_courses()
        courses = dynamodb_resource.Table("Courses")
        for course in enrolled_courses:
            stats = courses.get_item(
                Key={
                    'course_id': course.get("course_id")
                }
            ).get('Item')
            if stats:
                course["stats"] = {}
                course["stats"]["num_posts"] = stats.get("num_posts")
                course["stats"]["num_students"] = stats.get("num_students")
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
            Key={
                'course_id': course_id
            },
            ReturnValues='ALL_OLD'
        ).get('Attributes')

        if course_info is None or course_info.get('all_pids') is None:
            previous_all_pids = set()
        else:
            previous_all_pids = set([int(i) for i in course_info.get('all_pids')])

        try:
            feed = network.get_feed(limit=99999)['feed']
            all_pids = set([post['nr'] for post in feed])
            pids = all_pids.difference(previous_all_pids)
        except KeyError:
            print('Unable to get feed for course_id: {}'
                  .format(course_id))
            return False, None

        posts = get_course_table(course_id)

        current_pids = set()
        start_time = time.time()
        for pid in pids:
            # Get the post if available
            try:
                post = network.get_post(pid)
            except RequestError:
                all_pids.remove(pid)
                continue

            # Skip deleted and private posts
            if post['status'] == 'deleted' or post['status'] == 'private':
                print("Deleted post with pid {} and course id {} from Posts".format(pid, course_id))
                all_pids.remove(pid)
                posts.delete_item(
                    Key={
                        "post_id": pid,
                    }
                )

            # If the post is neither deleted nor private, it should be in the db
            current_pids.add(pid)

            # TODO: Parse the type of the post, to indicate if the post is
            # a note/announcement

            # Extract the subject, body, and tags from post
            subject, body, tags, post_type = self._extract_question_details(post)

            # Extract number of unique views of the post
            num_views = post['unique_views']

            # Get creation time
            created = datetime.strptime(post['created'], DATETIME_FORMAT)
            # Extract number of unresolved followups (if any)
            num_unresolved_followups = self._extract_num_unresolved(post)

            # Extract the student and instructor answers if applicable
            s_answer, i_answer = self._extract_answers(post)

            # Extract the followups and feedbacks if applicable
            followups = self._extract_followups(post)

            # insert post and add to course's post list
            item = {
                "post_id": pid,
                "created": int(created.timestamp()),
                "subject": subject,
                "body": body,
                "tags": tags,
                "post_type": post_type,
                "s_answer": s_answer,
                "i_answer": i_answer,
                "followups": followups,
                "num_unresolved_followups": num_unresolved_followups,
                "num_views": num_views
            }
            cleaned_item = {k: v for k, v in item.items() if v is not None}
            try:
                posts.put_item(
                    Item=cleaned_item
                )
                train = True
            except ClientError as e:
                print(pid, item)
                print(e)
                current_pids.remove(pid)
                all_pids.remove(pid)
                continue

        deleted_pids = previous_all_pids - all_pids
        for pid in deleted_pids:
            all_pids.remove(pid)
            print("Deleted post with pid {} and course id {} from Posts".format(pid, course_id))
            posts.delete_item(
                Key={
                    "post_id": pid,
                }
            )
            train = True

        # TODO: Figure out another way to verify whether the current user has access to a class.
        # In the event the course_id was invalid or no posts were parsed, delete course object
        # TODO: Should we delete the table?
        if len(pids) != 0 and len(current_pids) == 0:
            print('Unable to parse posts for course: {}. Please '
                  'confirm that the piazza user has access to this '
                  'course'.format(course_id))
            return False, None
        end_time = time.time()
        time_elapsed = end_time - start_time
        print('Course updated. {} new posts scraped in: {:.2f}s'.format(len(current_pids), time_elapsed))

        try:
            all_users = str(len(network.get_all_users()))
        except RequestError:
            all_users = "N/A"

        courses.update_item(
            Key={
                'course_id': course_id
            },
            UpdateExpression='SET #pids = :pids, num_students = :num_students, num_posts = :num_posts',
            ExpressionAttributeNames={
                '#pids': 'all_pids'
            },
            ExpressionAttributeValues={
                ':pids': all_pids,
                ":num_students": all_users,
                ":num_posts": str(network.get_statistics()['total']['questions'])
            }
        )

        return True, train

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
        if parsed_body == "":
            parsed_body = None
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


def lambda_handler(event, context):
    print("Event: {}".format(event))
    print("Context: {}".format(context))
    if event.get("source") == 'aws.events':
        course_id = event.get("resources")[0].split('/')[1]
    elif event.get("source") == "parqr-api":
        parser = Parser()
        return parser.get_stats_for_enrolled_courses()
    else:
        course_id = event['course_id']
    print("Course ID: {}".format(course_id))

    parser = Parser()
    success, train = parser.update_posts(course_id)
    if success:
        print("Successfully parsed")
        if train:
            print("Sending posts to ModelTrain")
            lambda_client = boto3.client('lambda')
            payload = {
                "course_ids": [
                    course_id
                ]
            }
            lambda_client.invoke(
                FunctionName='Parqr-ModelTrain:PROD',
                InvocationType='Event',
                Payload=bytes(json.dumps(payload), encoding='utf8')
            )
    else:
        print("Error parsing")
