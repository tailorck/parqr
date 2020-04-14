from flask_restful import Resource
from flask import request
import boto3
import json


class Feedbacks(Resource):

    def post(self):
        # Validate the feedback data
        lambda_client = boto3.client('lambda')

        response = lambda_client.invoke(
            FunctionName='Feedbacks',
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(request.json), encoding='utf8')
        )

        return json.loads(response['Payload'].read().decode("utf-8"))
