import json
import boto3
from collections import defaultdict
import random


import numpy as np
from flask_restful import Resource
from flask import request


class StudentQuery(Resource):

    def post(self, course_id):
        # Replaced by direct call to lambda on API Gateway
        return {}, 200


class InstructorQuery(Resource):

    def post(self, course_id):
        # Not implemented
        return {}, 500
