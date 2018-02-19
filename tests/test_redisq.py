import time
import json
import os

import mock
import unittest

from app.api import register_class, deregister_class

from redis import Redis
from rq.job import Job
from rq import Queue, SimpleWorker
from rq_scheduler import Scheduler


course_id = 'j65vl23t'


class TestRQ(unittest.TestCase):

    @mock.patch('app.api.redis')
    def test_redis_exist(self, mock_redis):

        # case 1: cid does not exist, register cid
        mock_redis.exists.return_value = False
        register_class(cid=course_id)
        self.assertTrue(mock_redis.exists.called,
                        "Failed to call redis.exists(cid) in register_class")
        mock_redis.exists.assert_called_with(course_id)
        mock_redis.reset_mock()


        # case 2: cid exists, do not register cid
        mock_redis.exists.return_value = True
        try:
            register_class(cid=course_id)
        except Exception as e:
            self.assertTrue(mock_redis.exists.called,
                            "Failed to call redis.exists(cid) in register_class")
        mock_redis.reset_mock()


        # case 3: cid exists, deregister cid
        mock_redis.exists.return_value = True
        deregister_class(cid=course_id)
        self.assertTrue(mock_redis.exists.called,
                        "Failed to call redis.exists(cid) in deregister_class")
        mock_redis.exists.assert_called_with(course_id)
        mock_redis.reset_mock()


        # case 4: cid does not exist, cannot deregister cid
        try:
            deregister_class(cid=course_id)
        except Exception as e:
            self.assertTrue(mock_redis.exists.called,
                            "Failed to call redis.exists(cid) in deregister_class")


    @mock.patch('app.api.redis')
    def test_redis_get(self, mock_redis):

        # case 1: cid does not exist, cannot deregister cid
        mock_redis.exists.return_value = False
        try:
            deregister_class(cid=course_id)
        except Exception as e:
            self.assertFalse(mock_redis.get.called,
                        "Failed to not call redis.get(cid) in deregister_class")
        mock_redis.reset_mock()


        # case 2: cid , deregister cid
        mock_redis.exists.return_value = True
        deregister_class(cid=course_id)
        self.assertTrue(mock_redis.get.called,
                         "Failed to call redis.get(cid) in deregister_class")
        mock_redis.get.assert_called_with(course_id)



    @mock.patch('app.api.redis')
    def test_redis_set(self, mock_redis):

        # case 1: cid does not exist, register cid
        mock_redis.exists.return_value = False
        register_class(cid=course_id)
        self.assertTrue(mock_redis.set.called,
                        "Failed to call redis.set(cid, serial_ids) in register_class")
        mock_redis.reset_mock()

        # case 2: cid exists, do not register cid
        mock_redis.exists.return_value = True
        try:
            register_class(cid=course_id)
        except Exception as e:
            self.assertFalse(mock_redis.set.called,
                            "Failed to not call redis.set(cid, serial_ids) in register_class")


    @mock.patch('app.api.redis')
    def test_redis_delete(self, mock_redis):

        # case 1: cid exists, deregister cid
        mock_redis.exists.return_value = True
        deregister_class(cid=course_id)
        self.assertTrue(mock_redis.delete.called,
                        "Failed to call redis.delete(cid) in deregister_class")
        mock_redis.delete.assert_called_with(course_id)
        mock_redis.reset_mock()

        # case 2: cid does not exist, cannot deregister cid
        mock_redis.exists.return_value = False
        try:
            deregister_class(cid=course_id)
        except Exception as e:
            self.assertFalse(mock_redis.delete.called,
                             "Failed to not call redis.delete(cid) in deregister_class")


    @mock.patch('app.api.scheduler')
    @mock.patch('app.api.redis')
    def test_scheduler_schedule(self, mock_redis, mock_scheduler):

        # case 1: cid does not exist, register cid
        mock_redis.exists.return_value = False
        register_class(cid=course_id)
        self.assertTrue(mock_scheduler.schedule.called,
                        "Failed to call scheduler.schedule in register_class")
        mock_redis.reset_mock()
        mock_scheduler.reset_mock()


        # case 2: cid exists, cannot register cid
        mock_redis.exists.return_value = True
        try:
            register_class(cid=course_id)
        except Exception as e:
            self.assertFalse(mock_scheduler.schedule.called,
                             "Failed to not call scheduler.schedule in register_class")


    @mock.patch('app.api.scheduler')
    @mock.patch('app.api.redis')
    def test_scheduler_get_jobs(self, mock_redis, mock_scheduler):

        # case 1: cid exists, deregister cid
        mock_redis.exists.return_value = True
        deregister_class(cid=course_id)
        self.assertTrue(mock_scheduler.get_jobs.called,
                        "Failed to call scheduler.get_jobs in deregister_class")
        mock_redis.reset_mock()
        mock_scheduler.reset_mock()


        # case 2: cid does not exist, cannot deregister cid
        mock_redis.exists.return_value = False
        try:
            deregister_class(cid=course_id)
        except Exception as e:
            self.assertFalse(mock_scheduler.get_jobs.called,
                             "Failed to not call scheduler.get_jobs in register_class")


    # @mock.patch('app.api.scheduler')
    # @mock.patch('app.api.redis')
    # def test_scheduler_cancel(self, mock_redis, mock_scheduler):
    #
    #     # case 1: cid exists, deregister cid
    #     mock_redis.exists.return_value = True
    #     deregister_class(cid=course_id)
    #     self.assertTrue(mock_scheduler.cancel.called,
    #                     "Failed to call scheduler.cancel in deregister_class")
    #     mock_redis.reset_mock()
    #     mock_scheduler.reset_mock()
    #
    #
    #     # case 2: cid does not exist, cannot deregister cid
    #     mock_redis.exists.return_value = False
    #     try:
    #         deregister_class(cid=course_id)
    #     except Exception as e:
    #         self.assertFalse(mock_scheduler.cancel.called,
    #                          "Failed to not call scheduler.cancel in register_class")
