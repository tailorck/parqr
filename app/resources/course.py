from datetime import datetime

from flask_restful import Resource, reqparse
from flask_jwt import jwt_required
from flask import jsonify

from app.tasksrq import parse_and_train_models
from app.constants import (
    COURSE_PARSE_TRAIN_TIMEOUT_S,
    COURSE_PARSE_TRAIN_INTERVAL_S
)
from app.extensions import (
    scheduler,
    logger,
    redis,
    parser
)


def mark_active_courses(course_list):
    for course in course_list:
        course['active'] = redis.exists(course.get('course_id', None))

    return course_list


class CoursesList(Resource):

    def __init__(self):
        self.enrolled_courses = parser.get_enrolled_courses()
        self.enrolled_courses = mark_active_courses(self.enrolled_courses)

    @jwt_required()
    def get(self):
        arg_parser = reqparse.RequestParser()
        arg_parser.add_argument('active', type=bool)
        args = arg_parser.parse_args()

        if args.active:
            return jsonify(list(filter(lambda x: x['active'], self.enrolled_courses)))
        else:
            return jsonify(self.enrolled_courses)


class ActiveCourse(Resource):

    def __init__(self):
        self.enrolled_courses = parser.get_enrolled_courses()
        self.enrolled_courses = mark_active_courses(self.enrolled_courses)

    @jwt_required()
    def get(self, course_id):
        return jsonify(list(filter(lambda x: x['active'], self.enrolled_courses)))

    @jwt_required()
    def post(self, course_id):
        """
        instructor registers the class
        :return:
        """
        valid_course_id = False
        for course in self.enrolled_courses:
            if course.get('course_id') == course_id:
                valid_course_id = True

        if not valid_course_id:
            return {'message': 'PARQR is not enrolled in course with id {}'.format(course_id)}, 409

        if redis.exists(course_id):
            return {'message': 'Course with id {} is already registered'.format(course_id)}, 409
        else:
            logger.info('Registering new course with id: {}'.format(course_id))

            new_course_job = scheduler.schedule(scheduled_time=datetime.now(),
                                                func=parse_and_train_models,
                                                kwargs={"course_id": course_id},
                                                interval=COURSE_PARSE_TRAIN_INTERVAL_S,
                                                timeout=COURSE_PARSE_TRAIN_TIMEOUT_S)
            redis.set(course_id, new_course_job.id)
            return {'message': 'Course id {} registered'.format(course_id)}, 201

    @jwt_required()
    def delete(self, course_id):
        if redis.exists(course_id):
            logger.info('Deregistering course: {}'.format(course_id))
            job_id_str = redis.get(course_id)
            scheduler.cancel(job_id_str)
            redis.delete(course_id)
            return {'message': 'Course id {} deregistered'.format(course_id)}, 201
        else:
            return {'message': 'Course id {} does not exists'.format(course_id)}, 409

