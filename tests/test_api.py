import unittest
import mock
import json
from decimal import Decimal
import pytest


class TestHelloWorldAPI(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict('os.environ', {'stage': 'prod'})
        with self.env:
            from app import api
            self.test_app = api.app.test_client()

    def test_hello_world(self):
            res = self.test_app.get("/prod/")
            assert res.status_code == 200
            assert b"Hello, World!" in res.data


def mock_mark_active_courses(courses):
    return json.loads('[{"active": true, "course_id": "j8rf9vx65vl23t", "course_num": "CS '
                      '007", "name": "Parqr Test Course", "term": "Fall 2017"}]')


def mock_get_enrolled_courses_from_piazza():
    return json.loads(
        '[{"course_id": "j8rf9vx65vl23t", "course_num": "CS '                                           '007", '
        '"name": "Parqr Test Course", "term": "Fall 2017"}] ')


class TestCoursesAPI(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict('os.environ', {'stage': 'prod'})
        with self.env:
            from app import api
            self.test_app = api.app.test_client()

    @mock.patch('app.resources.course.mark_active_courses', side_effect=mock_mark_active_courses)
    @mock.patch('app.resources.course.get_enrolled_courses_from_piazza',
                side_effect=mock_get_enrolled_courses_from_piazza)
    def test_get(self, mock_mark_active_courses_function, mock_boto_function):
        res = self.test_app.get('/prod/courses')
        assert res.status_code == 200


class TestCourseAPI(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict('os.environ', {'stage': 'prod'})
        with self.env:
            from app import api
            self.test_app = api.app.test_client()

        self.res_data = {
            "name": "Parqr Test Course",
            "course_id": "j8rf9vx65vl23t",
            "term": "Fall 2017",
            "course_num": "CS 007",
            "active": True
        }

    @mock.patch('app.resources.course.mark_active_courses',
                side_effect=mock_mark_active_courses)
    @mock.patch('app.resources.course.get_enrolled_courses_from_piazza',
                side_effect=mock_get_enrolled_courses_from_piazza)
    def test_get(self, mock_get_enrolled_courses_from_piazza_function, mock_mark_active_courses_function):
        res = self.test_app.get("/prod/courses/j8rf9vx65vl23t")
        assert res.status_code == 200
        assert self.res_data == json.loads(res.data)


class TestActiveCourseAPI(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict('os.environ', {'stage': 'prod'})
        with self.env:
            from app import api
            self.test_app = api.app.test_client()

        self.res_data = b'{"active": true, "course_id": "j8rf9vx65vl23t", "course_num": "CS 007", "name": "Parqr Test Course", "term": "Fall 2017"}\n'

    @mock.patch('app.resources.course.mark_active_courses', side_effect=mock_mark_active_courses)
    @mock.patch('app.resources.course.get_enrolled_courses_from_piazza',
                side_effect=mock_get_enrolled_courses_from_piazza)
    def test_get(self, mock_mark_active_courses_function, mock_get_enrolled_courses_from_piazza_active_function):
        res = self.test_app.get('/prod/courses/j8rf9vx65vl23t/active')

        assert res.status_code == 200
        assert res.data == self.res_data


def mock_get_posts_table(course_id):
    mock_boto3 = mock.Mock()
    mock_boto3.scan.return_value = {
        "Items": [
            {
                'subject': 'oh henlo',
                'post_type': 'question',
                'num_unresolved_followups': Decimal('0'),
                'followups': [],
                'course_id': 'j8rf9vx65vl23t',
                'post_id': Decimal('18'),
                'created': Decimal('1581482976'),
                'num_views': Decimal('2'),
                'tags': ['hw4', 'student', 'unanswered'],
                'body': 'wassup'
            }
        ]
    }
    return mock_boto3


class TestStudentRecommendationAPI(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict('os.environ', {'stage': 'prod'})
        with self.env:
            from app import api
            self.test_app = api.app.test_client()

    @mock.patch('app.statistics.get_posts_table', side_effect=mock_get_posts_table)
    def test_get(self, mock_get_posts_table_function):
        res = self.test_app.get('/prod/courses/j8rf9vx65vl23t/recommendation/student')
        assert json.loads(res.data)["message"] == "success"


if __name__ == "__main__":
    unittest.main()
