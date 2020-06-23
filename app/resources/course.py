import json
import os
import time

import boto3
from flask_restful import Resource, reqparse
# from flask_jwt import jwt_required
from flask import jsonify, request


def get_boto3_events():
    return boto3.client('events')


def get_boto3_lambda():
    return boto3.client('lambda')


def get_boto3_s3():
    return boto3.client('s3')


def get_enrolled_courses_from_piazza():
    if os.path.exists("/tmp/courses.json"):
        print("Loading courses found in /tmp")
        with open("/tmp/courses.json", "r") as input_file:
            courses = json.load(input_file)
            return courses
    else:
        print("Getting courses from s3")
        s3 = get_boto3_s3()

        response = s3.get_object(
            Bucket='parqr',
            Key='courses.json'
        )
        courses = json.loads(response['Body'].read().decode("utf-8"))
        with open("/tmp/courses.json", "w") as input_file:
            json.dump(courses, input_file)

        return courses


def mark_active_courses(course_list):
    events = get_boto3_events()
    boto3_lambda = get_boto3_lambda()

    print("Course List: {}".format(course_list))

    # Get the Function arn for Parser
    target_arn = boto3_lambda.get_function(
        FunctionName='Parser:PROD'
    ).get('Configuration').get('FunctionArn')

    # Get all the courses that currently have rules that target Parser
    response = events.list_rule_names_by_target(
        TargetArn=target_arn
    )
    rule_names = response.get('RuleNames')
    while response.get('NextToken') is not None:
        next_token = response.get('NextToken')
        response = events.list_rule_names_by_target(
            TargetArn=target_arn,
            NextToken=next_token
        )
        rule_names.extend(response.get('RuleNames'))

    print("Rule Names targeting Parser: {}".format(rule_names))

    for course in course_list:
        # Check if the course_id has a rule, if it does not, then it is disabled
        if course.get('course_id') in rule_names:
            response = events.describe_rule(
                Name=course.get('course_id')
            )

            # Check if a rule is enabled
            if response.get('State') == 'ENABLED':
                course['active'] = True
            else:
                course['active'] = False
        else:
            course['active'] = False

    return course_list


class CoursesList(Resource):

    def __init__(self):
        start = time.time()
        self.enrolled_courses = get_enrolled_courses_from_piazza()
        end = time.time()
        print("{} seconds to get courses from piazza".format(end - start))
        start = time.time()
        self.enrolled_courses = mark_active_courses(self.enrolled_courses)
        end = time.time()
        print("{} seconds to mark courses active".format(end - start))

    # @jwt_required()
    def get(self):
        start = time.time()
        arg_parser = reqparse.RequestParser()
        arg_parser.add_argument('active', type=bool)
        args = arg_parser.parse_args()
        end = time.time()
        print("{} seconds to parse args".format(end - start))

        if args.active:
            return jsonify(list(filter(lambda x: x['active'], self.enrolled_courses)))
        else:
            return jsonify(self.enrolled_courses)


class ActiveCourse(Resource):

    def __init__(self):
        self.enrolled_courses = get_enrolled_courses_from_piazza()
        self.enrolled_courses = mark_active_courses(self.enrolled_courses)

    # @jwt_required()
    def get(self, course_id):
        active_course = None
        for course in self.enrolled_courses:
            if course.get('course_id') == course_id:
                active_course = course

        if not active_course:
            return {
                       "course_id": course_id,
                       "active": False
                   }, 200

        return active_course, 200

    # @jwt_required()
    def post(self, course_id):
        """
        instructor registers the class
        :return:
        """
        print('Registering new course: {}'.format(course_id))

        if os.path.exists("/tmp/courses.json"):
            os.remove("/tmp/courses.json")
        valid_course_id = False
        course_info = ""
        for course in self.enrolled_courses:
            if course.get('course_id') == course_id:
                valid_course_id = True
                course_info = " ".join([course.get("term"), course.get("course_num"), course.get('name')])
                break

        if not valid_course_id:
            return {'message': 'PARQR is not enrolled in course with id {}'.format(course_id)}, 409

        # Create a new event as a cloud cron job
        cloudwatch_events = get_boto3_events()

        # Check if course is already registered
        try:
            cloudwatch_events.enable_rule(
                Name=course_id
            )
            print("Course already registered in PARQR")
            return {
                       'course_id': course_id,
                       "active": True
                   }, 200
        except cloudwatch_events.exceptions.ResourceNotFoundException:
            pass

        rule_arn = cloudwatch_events.put_rule(
            Name=course_id,
            ScheduleExpression='rate(15 minutes)',
            State='ENABLED',
            Description=course_info
        ).get('RuleArn')

        if not rule_arn:
            print("{}: Error creating cloudwatch event".format(course_id))
            return {'message': 'Internal Server Error'}, 500

        # Create a lambda permission object so cloudwatch events can call the lambda
        lambda_client = get_boto3_lambda()
        # TODO: Inject new environment variable based upon master or dev
        lambda_response = lambda_client.get_function(
            FunctionName="Parser:PROD"
        )

        # Set the lambda as the cloudwatch event target
        lambda_arn = lambda_response.get('Configuration').get('FunctionArn')
        target_response = cloudwatch_events.put_targets(
            Rule=course_id,
            Targets=[
                {
                    'Id': "{}-{}".format(course_id, str(int(time.time()))),
                    'Arn': lambda_arn
                }
            ]
        )

        if target_response.get('FailedEntryCount') > 0:
            print("Error putting cloudwatch event target")
            return {'message': 'Internal Server Error'}, 500

        payload = {
            "source": "parqr-api"
        }
        lambda_client.invoke(
            FunctionName='Parser:PROD',
            InvocationType='Event',
            Payload=bytes(json.dumps(payload), encoding='utf8')
        )

        response = {
            'course_id': course_id,
            "active": True
        }
        return response, 200

    # @jwt_required()
    def delete(self, course_id):
        print('Deregistering course: {}'.format(course_id))

        if os.path.exists("/tmp/courses.json"):
            os.remove("/tmp/courses.json")
        # TODO: Could this throw an exception?
        cloudwatch_events = get_boto3_events()
        cloudwatch_events.disable_rule(
            Name=course_id
        )

        lambda_client = get_boto3_lambda()
        payload = {
            "source": "parqr-api"
        }
        lambda_client.invoke(
            FunctionName='Parser:PROD',
            InvocationType='Event',
            Payload=bytes(json.dumps(payload), encoding='utf8')
        )

        return {
                   "course_id": course_id,
                   "active": False
               }, 200


class FindCourseByCourseID(Resource):

    def __init__(self):
        self.enrolled_courses = get_enrolled_courses_from_piazza()
        self.enrolled_courses = mark_active_courses(self.enrolled_courses)

    def get(self, course_id):
        course = next(filter(lambda x: x['course_id'] == course_id, self.enrolled_courses), None)

        if not course:
            return {'message': 'Course is not enrolled.'}, 400

        return course, 200
