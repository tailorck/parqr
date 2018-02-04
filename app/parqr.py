from datetime import datetime, timedelta
import logging

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd

from models import Post
from utils import clean, ModelCache
from constants import TFIDF_MODELS, SCORE_THRESHOLD

logger = logging.getLogger('app')


class ModelInfo(object):

    def __init__(self, model_name, vectorizer=None, matrix=None,
                 post_ids=None):
        self.name = model_name
        self._vectorizer = vectorizer
        self._matrix = matrix
        self._post_ids = post_ids

    @property
    def vectorizer(self):
        return self._vectorizer

    @property
    def matrix(self):
        return self._matrix

    @property
    def post_ids(self):
        return self._post_ids


class CourseInfo(object):

    def __init__(self, cid):
        self.cid = cid
        self.models = {}
        self._last_load = None

    @property
    def last_load(self):
        return self._last_load

    @last_load.setter
    def last_load(self, new_time):
        self._last_load = new_time


class Parqr(object):

    def __init__(self):
        """Initializes private caching dictionaries."""
        self._course_dict = {}
        self._model_cache = ModelCache('app/resources')

    def get_recommendations(self, cid, query, N):
        """Get the N most similar posts to provided query.

        Parameters
        ----------
        cid : str
            The course id of the class found in the url
        query : str
            A query string to perform comparison on
        N : int
            The number of similar posts to return

        Returns
        -------
        top_posts : dict
            A sorted dict of the top N most similar posts with their similarity
            scores as the keys
        """
        logger.info('Retrieving similar posts for query.')

        # clean query vector
        clean_query = clean(query)

        # Retrive the scores for each model in the course as a pandas DataFrame
        tfidf_scores = self._get_tfidf_recommendations(cid, clean_query, N)

        # Take a weighted combination of the scores from each model
        weights = pd.DataFrame([0.4, 0.2, 0.2, 0.2], index=list(TFIDF_MODELS))
        final_scores = tfidf_scores.dot(weights)
        final_scores.columns = ['scores']
        final_scores.sort_values(by=['scores'], ascending=False, inplace=True)

        # Return post id, subject, and score for the top N scores in the df
        top_posts = {}
        for pid in final_scores.index[:N]:
            post = Post.objects.get(cid=cid, pid=pid)
            score = final_scores.loc[pid][0]
            subject = post.subject
            s_answer = True if post.s_answer != None else False
            i_answer = True if post.i_answer != None else False

            if score > SCORE_THRESHOLD:
                top_posts[score] = {'pid': pid,
                                    'subject': subject,
                                    's_answer': s_answer,
                                    'i_answer': i_answer}

        return top_posts

    def _get_tfidf_recommendations(self, cid, query, N):
        """Scores the query for all the models in a given course.

        This function iterates over all the models for a given course,
        vectorizes the query into the model's vector-space, and computes the
        similarity to all the all the other posts in the class in the model's
        vector-space. All the scores are stored as columns in a pd.DataFrame

        Args:
            cid (str): The course id of interest
            query (str): The cleaned version of the original query
            N (int): The number of similar posts to return for each model

        Returns:
            pd.DataFrame: A dataframe of all the scores for the course indexed
                on the valid pids of the course and each column representing
                the score from each model
        """

        # Retrieve all the valid pids for a course since some pids are private
        # or deleted
        all_pids = self._get_all_pids(cid)
        tfidf_scores = pd.DataFrame(index=all_pids)
        now = datetime.now()
        delay = timedelta(minutes=30)

        # If the models for a course are not loaded into memory or it has been
        # some time since they were loaded last, reload them.
        if cid not in self._course_dict:
            self._load_all_models(cid)
        elif now - self._course_dict[cid].last_load > delay:
            logger.info('Reloading models for cid: {}'.format(cid))
            self._load_all_models(cid)

        course_info = self._course_dict[cid]
        for model_name in TFIDF_MODELS:
            # Retrieve the appropriate vectorizer for this course, a matrix
            # where each row represents a post in the course in vector form.
            vectorizer = course_info.models[model_name].vectorizer
            matrix = course_info.models[model_name].matrix

            # We also need to retrieve the post_ids for this particular model
            # to map the rows in the matrix to the pid of the post in the
            # course.
            post_ids = course_info.models[model_name].post_ids

            # If a particular model for a course does not exist, then set the
            # contributions of said model to the final score of each pid to
            # all zeros
            if vectorizer is None or matrix is None:
                tfidf_scores.loc[all_pids, model_name] = np.zeros(len(all_pids))
                continue

            # The transform method takes an iterable as input. The string does
            # not need to be tokenized, just placed in a list. This method will
            # convert the query string of words into a vector in the TF-IDF
            # vector space
            q_vector = vectorizer.transform([query])

            # Calculate the similarity score for query vector with all vectors
            # in the course matrix. The matrix contains all the posts of course
            # in vectorized form.
            scores = cosine_similarity(q_vector, matrix)[0]

            # Now we index into our scores dataframe and set the contribution
            # of this particular model to the final score. Each model will only
            # be able to contribute to the score
            tfidf_scores.loc[post_ids, model_name] = scores

        tfidf_scores.fillna(0, inplace=True)
        return tfidf_scores

    def _load_all_models(self, cid):
        """Uses the ModelCache class to load the sklearn model, matrix, and
        post_ids that are stored on disk into memory.

        Args:
            cid (str): The course id of interest
        """
        logger.info("Loading all models for cid: {}".format(cid))

        if cid not in self._course_dict:
            self._course_dict[cid] = CourseInfo(cid)

        course_info = self._course_dict[cid]
        for model_name in TFIDF_MODELS:
            skmodel, matrix, pid_list = self._model_cache.get_all(cid, model_name)
            course_info.models[model_name] = ModelInfo(model_name, skmodel,
                                                       matrix, pid_list)

        course_info.last_load = datetime.now()

    def _get_all_pids(self, cid):
        """Retrives the valid post_ids for a particular course.

        Not all post_ids are valid in a given course since the scraper ignores
        deleted posts and private posts.

        Args:
            cid (str): The course id of interest

        Returns:
            list: A list of all the valid post_ids
        """
        pids = []
        for post in Post.objects(cid=cid):
            pids.append(post.pid)

        return pids
