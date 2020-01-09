from flask_restful import Resource
from app.models.course import Course
from flask import request
from app.extensions import feedback, parqr, logger
from app.utils import verify_non_empty_json_request
from collections import defaultdict
from app.models.post import Post
import json

with open('related_courses.json') as f:
    related_courses = json.load(f)


class StudentQuery(Resource):

    @verify_non_empty_json_request
    def post(self):
        """
        Given course_id and query, retrieve 5 similar posts
        :return:
        """
        course_id = request.json['course_id']
        if not Course.objects(course_id=course_id):
            logger.error('New un-registered course found: {}'.format(course_id))
            return {'message': "Course with course id {} not supported at this "
                               "time.".format(course_id)}, 400

        query = request.json['query']
        similar_posts = parqr.get_recommendations(course_id, query, 5)
        if feedback.requires_feedback():
            query_rec_id = feedback.save_query_rec_pair(course_id, query, similar_posts)
            similar_posts = feedback.update_recommendations(query_rec_id, similar_posts)

        return similar_posts


class InstructorQuery(Resource):

    @verify_non_empty_json_request
    def post(self):
        course_id = request.json['course_id']
        if not Course.objects(course_id=course_id) or course_id not in related_courses:
            logger.error('New un-registered course found: {}'.format(course_id))
            return {'message': "Course with course id {} not supported at this "
                               "time.".format(course_id)}, 400

        query = request.json['query']

        response = defaultdict(list)
        for rel_course_id in related_courses[course_id]:
            if not Course.objects(course_id=rel_course_id):
                continue

            recs = parqr.get_recommendations(rel_course_id, query, 5)
            recs_post_ids = [rec['pid'] for rec in recs.values()]
            recommended_posts = Post.objects(course_id=rel_course_id,
                                             post_id__in=recs_post_ids)

            for post in recommended_posts:
                if post.i_answer is not None:
                    response[rel_course_id].append({
                        "post_id": post.post_id,
                        "student_subject": post.subject,
                        "student_post": post.body,
                        "instructor_answer": post.i_answer
                    })

        return response
