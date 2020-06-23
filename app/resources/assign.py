from flask import request
from flask_restful import Resource
import boto3
import os


def get_posts_table(course_id):
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table(course_id)


class ResolvePost(Resource):

    def post(self, course_id):
        post_id = request.json.get('post_id')
        resolved = bool(request.json.get('resolved'))

        posts = get_posts_table(course_id)
        posts.update_item(
            Key={
                "post_id": int(post_id)
            },
            UpdateExpression="SET resolved = :resolved",
            ExpressionAttributeValues={
                ":resolved": resolved
            }
        )

        filename = "".join(["/tmp/instructor-", course_id, ".json"])
        if os.path.exists(filename):
            os.remove(filename)

        return {'message': 'success'}, 200


class AssignInstructor(Resource):

    def post(self, course_id):
        assignee = request.json.get('assignee')
        post_id = request.json.get('post_id')
        assign = bool(request.json.get('assign'))

        if assign:
            posts = get_posts_table(course_id)
            posts.update_item(
                Key={
                    "post_id": int(post_id)
                },
                UpdateExpression="ADD assignees :assignee",
                ExpressionAttributeValues={
                    ":assignee": {assignee}
                }
            )
        else:
            posts = get_posts_table(course_id)
            posts.update_item(
                Key={
                    "post_id": int(post_id)
                },
                UpdateExpression="DELETE assignees :assignee",
                ExpressionAttributeValues={
                    ":assignee": {assignee}
                }
            )

        filename = os.path.join("/tmp/instructor-", course_id, ".json")
        if os.path.exists(filename):
            os.remove(filename)

        return {'message': 'success'}, 200
