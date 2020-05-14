import uuid

import json
import boto3
import numpy as np
from app.constants import (
    FEEDBACK_MAX_RATING,
    FEEDBACK_MIN_RATING
)


class Feedback(object):

    def __init__(self, max_rating, min_rating, feedback_probability=0.1):
        """ Initialization
            Parameters
            ----------
            max_rating : int
                The maximum rating to accept for a post
            min_rating : int
                The minimum rating to accept for a post
        """
        self.max_rating = max_rating
        self.min_rating = min_rating
        self.feedback_probability = feedback_probability

    def requires_feedback(self):
        """ Probalisticly decides whether to request feedback from the user or not.

        Returns:
            requires_feedback (bool): Whether to request feedback or not.
        """
        return np.random.random_sample() < self.feedback_probability

    def update_recommendations(self, query_rec_id, similar_posts):
        """ Updates a set of recommendations to instruct frontend to provide feedback.

        Args:
            query_rec_id: The query recommendation pair ID used as the primary key in DynamoDB
            similar_posts: A dictionary of recommendations provided to the user

        Returns:
            similar_posts (dict): A dictionary of recommendations with the feedback flag set

        """
        for obj in similar_posts:
            obj['feedback'] = True
            obj['query_rec_id'] = query_rec_id
        return similar_posts

    def save_query_rec_pair(self, course_id, query, similar_posts):
        """ Given a course id, a query string, and a set of recommendations for query, store into DynamoDB to track
        feedback

        Args:
            course_id: The course id for the query recommendation pair
            query: The query that was provided by the user
            similar_posts: The set of recommendations provided by our algorithm

        Returns:
            query_rec_id (str): The primary key for query recommendation id in DynamoDB
        """
        recommended_pids = [similar_posts[score]["pid"] for score in similar_posts.keys()]

        dynamodb = boto3.client('dynamodb')
        query_rec_id = uuid.uuid4()
        query_recommendation_pair = {
            'course_id': course_id,
            'uuid': query_rec_id,
            'query': query,
            'recommended_pids': recommended_pids
        }

        dynamodb.put_item(
            TableName='Feedbacks',
            Item=query_recommendation_pair
        )

        return query_rec_id

    def validate_feedback(self, query_rec_id, feedback_pid, user_rating):
        """ Performs a sanity check on the feedback. Returns true if the feedback is in a valid format and holds valid
        data. Returns false otherwise.

        Args:
            query_rec_id: The query recommendation pair primary key in DynamoDB
            feedback_pid: The post ID of the post that the feedback was selected for
            user_rating: The rating provided by the user

        Returns:
            valid_feedback (bool): Whether the input checks out or not
        """
        # Check that the user rating are within the accepted limits
        if (user_rating < self.min_rating) or (user_rating > self.max_rating):
            return False, "Rating must be between {} and {}.".format(self.min_rating, self.max_rating)

        # Check that the query-recommendation pair exists
        dynamodb = boto3.client('dynamodb')
        response = dynamodb.get_item(
            TableName='Feedbacks',
            Key={
                'uuid': {
                    'S': query_rec_id
                }
            }
        )
        print(response)
        query_rec_pair = response.get("Item")
        if not query_rec_pair:
            return False, "The query-recommendation id {} does not exist.".format(query_rec_id)

        # Check that the query string isn't empty
        query = query_rec_pair.get("query").get('S')

        if not query:
            return False, "Invalid query string."

        # Check that the feedback is for a post that was actually recommended
        recommended_pids = json.loads(query_rec_pair.get("recommended_pids").get('S'))

        if feedback_pid not in recommended_pids:
            return False, "The post id {} is not in the list of suggested posts ids {}.".format(feedback_pid,
                                                                                                recommended_pids)

        return True, query_rec_pair

    @staticmethod
    def register_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating):
        """ Registers given feedback in the database.

        Args:
            query_rec_id: The primary key for query recommendation pair
            user_rating: The rating provided by the user

        Returns:
            success (bool): Whether the feedback was successfully registered
        """
        dynamodb = boto3.client('dynamodb')
        query_rec_pair = dynamodb.get_item(
            TableName='Feedbacks',
            Key={
                'uuid': {
                    'S': query_rec_id
                }
            }
        ).get("Item")

        # If it doesn't exist, return failure
        if not query_rec_pair:
            dynamodb.put_item(
                Item={
                    'query_rec_id': query_rec_id,
                    'user_id': user_id,
                    'feedback_pid': feedback_pid,
                    'user_rating': user_rating,
                    'course_id': course_id
                }
            )
        else:
            # Record the feedback
            dynamodb.update_item(
                TableName='Feedbacks',
                Key={
                    'uuid': {
                        'S': query_rec_id
                    }
                },
                UpdateExpression="set user_rating = :user_rating_val",
                ExpressionAttributeValues={
                    ":user_rating_val": {
                        'N': str(user_rating)
                    }
                }
            )

        return True

    @staticmethod
    def unpack_feedback(feedback):
        """ Given a feedback dictionary, unpack it to retrieve its components

        Args:
            feedback: A dictionary with feedback information

        Returns:
            course_id, user_id, query_rec_id, feedback_pid, user_rating
        """
        course_id = feedback["course_id"]
        user_id = feedback["user_id"]
        query_rec_id = feedback["query_rec_id"]
        feedback_pid = feedback["feedback_pid"]
        user_rating = feedback["user_rating"]

        return course_id, user_id, query_rec_id, feedback_pid, user_rating


def lambda_handler(event, context):
    print(event)
    feedback = Feedback(FEEDBACK_MAX_RATING, FEEDBACK_MIN_RATING)
    if event.get("source") == "query":
        similar_posts = event.get("similar_posts")
        course_id = event.get("course_id")
        query = event.get("query")

        query_rec_id = feedback.save_query_rec_pair(course_id, query, similar_posts)
        similar_posts = feedback.update_recommendations(query_rec_id, similar_posts)

        return {"similar_posts": similar_posts}
    else:
        course_id, user_id, query_rec_id, feedback_pid, user_rating = feedback.unpack_feedback(event)
        valid, message = feedback.validate_feedback(query_rec_id, feedback_pid, user_rating)

        # If not failed, return invalid usage
        if not valid:
            return {'message': "Feedback contains invalid data." + message}, 400

        success = Feedback.register_feedback(course_id, user_id, query_rec_id, feedback_pid, user_rating)

        if success:
            return {'message': 'success'}, 200

        else:
            return {'message': 'failure'}, 500
