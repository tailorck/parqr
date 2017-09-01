import unittest
import pdb
import re

from app.models import Post
from app.parqr import Parqr
from app.utils import clean


class TestRecommendations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parqr = Parqr()

    def extract_pids(self, responses):
        return [response['pid'] for response in responses.values()]

    @unittest.skip("Bad unit test")
    def test_only_link_responses(self):
        only_post_link = re.compile('^@\d+$')
        only_link_responses = Post.objects(i_answer=only_post_link)
        for post in only_link_responses:
            instructor_pid = int(post.i_answer.split('@')[1])
            query = clean(post.body)
            responses = self.parqr.get_similar_posts(post.cid, query, 10)
            suggested_pids = self.extract_pids(responses)
            self.assertIn(instructor_pid, suggested_pids)
