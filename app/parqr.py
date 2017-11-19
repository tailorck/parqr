from enum import Enum
from multiprocessing.dummy import Pool
from functools import partial
import logging
import pdb

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction import text
import numpy as np
import pandas as pd

from app.exception import InvalidUsage
from app.models import Course, Post
from app.utils import clean, clean_and_split, stringify_followups
from constants import TFIDF_MODELS
import constants


class Parqr():

    def __init__(self, verbose=False):
        """Initializes private caching dictionaries.

        Parameters
        ----------
        verbose : boolean
            A boolean to instruct module to output informative log statements.
        """
        self.verbose = verbose
        if self.verbose == True:
            self._logger = logging.getLogger('app')
        self._vectorizers = {}
        self._matrices = {}
        self._post_ids = {}

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
        if self.verbose:
            self._logger.info('Retrieving similar posts for query.')

        # clean query vector
        clean_query = clean(query)

        tfidf_scores = self._get_tfidf_recommendations(cid, query, N)
        weights = pd.DataFrame([0.4, 0.2, 0.2, 0.2], index=list(TFIDF_MODELS))

        final_scores = tfidf_scores.dot(weights)
        final_scores.columns = ['scores']
        final_scores.sort_values(by=['scores'], ascending=False, inplace=True)

        # Return post id, subject, and score
        top_posts = {}
        for pid in final_scores.index[:N]:
            post = Post.objects.get(cid=cid, pid=pid)
            score = final_scores.loc[pid][0]
            subject = post.subject
            stud_answer = True if post.s_answer != None else False
            inst_answer = True if post.i_answer != None else False

            if score > constants.SCORE_THRESHOLD:
                top_posts[score] = {'pid': pid,
                                    'subject': subject,
                                    's_answer': stud_answer,
                                    'i_answer': inst_answer}

        return top_posts

    def _get_tfidf_recommendations(self, cid, query, N):
        all_pids = self._get_all_pids(cid)
        tfidf_scores = pd.DataFrame(index=all_pids)
        for model in TFIDF_MODELS:
            # retrieve the appropriate vectorizer and pre-computed TF-IDF
            # Matrix # for this course, or create new ones if they do not exist
            if cid not in self._vectorizers or cid not in self._matrices:
                self._vectorize_posts(cid)

            vectorizer = self._vectorizers[cid][model]
            matrix = self._matrices[cid][model]

            if vectorizer is None or matrix is None:
                tfidf_scores.loc[all_pids, model] = np.zeros(len(all_pids))
                continue

            # the transform method takes an iterable as input. The string does
            # not need to be tokenized, just placed in a list
            q_vector = vectorizer.transform([query])

            # calculate the similarity score for query with all vectors in
            # matrix
            scores = cosine_similarity(q_vector, matrix)[0]

            # retrieve the index of the vectors with the highest similarity.
            # np.argsort naturally sorts in ascending order, so the list must
            # be reversed and the top N most similar posts are stored
            top_N_vector_indices = np.argsort(scores)[::-1][:N]

            # the index of the vector in the matrix does not directly
            # correspond to the pid of the associated post, so the vector
            # indices must be mapped to course post ids
            top_N_pids = self._post_ids[cid][model][top_N_vector_indices]

            tfidf_scores.loc[top_N_pids, model] = scores[top_N_vector_indices]

        tfidf_scores.fillna(0, inplace=True)
        return tfidf_scores

    def _vectorize_posts(self, cid):
        """Vectorizes he list of post words into a TF-IDF Matrix

        Parameters
        ----------
        cid : str
            The course id of the class found in the url

        Returns
        -------
        vectorizer : TfidfVectorizer
            The trained TF-IDF vectorizer object that can be used to convert
            text to vectors.
        tfidf_matrix : np.array
            Tf-idf-weighted document-term matrix.
        """
        if self.verbose:
            self._logger.info('Vectorizing words from posts list')

        pool = Pool(4)
        func = partial(self._create_model, cid)
        results = pool.map(func, list(TFIDF_MODELS))
        pool.close()
        pool.join()

        if self.verbose:
            self._logger.info('Finished Vectorizing')

        return pool

    def _create_model(self, cid, model):
        stop_words = set(text.ENGLISH_STOP_WORDS)
        words = self._get_words_for_model(cid, model)

        if words.size != 0:
            vectorizer = text.TfidfVectorizer(analyzer='word',
                                              stop_words=stop_words)
            matrix = vectorizer.fit_transform(words)
        else:
            vectorizer = None
            matrix = None

        if cid not in self._vectorizers or cid not in self._matrices:
            self._vectorizers[cid] = {}
            self._matrices[cid] = {}

        self._vectorizers[cid][model] = vectorizer
        self._matrices[cid][model] = matrix

    def _get_words_for_model(self, cid, model):
        words = []
        model_pid_list = []

        for post in Post.objects(cid=cid):
            if model == TFIDF_MODELS.POST:
                clean_subject = clean_and_split(post.subject)
                clean_body = clean_and_split(post.body)
                tags = post.tags
                words.append(' '.join(clean_subject + clean_body + tags))
                model_pid_list.append(post.pid)
            elif model == TFIDF_MODELS.I_ANSWER:
                if post.i_answer:
                    words.append(' '.join(clean_and_split(post.i_answer)))
                    model_pid_list.append(post.pid)
            elif model == TFIDF_MODELS.S_ANSWER:
                if post.s_answer:
                    words.append(' '.join(clean_and_split(post.s_answer)))
                    model_pid_list.append(post.pid)
            elif model == TFIDF_MODELS.FOLLOWUP:
                if post.followups:
                    followup_str = stringify_followups(post.followups)
                    words.append(' '.join(clean_and_split(followup_str)))
                    model_pid_list.append(post.pid)

        if cid not in self._post_ids:
            self._post_ids[cid] = {}

        self._post_ids[cid][model] = np.array(model_pid_list)

        return np.array(words)

    def _get_all_pids(self, cid):
        pids = []
        for post in Post.objects(cid=cid):
            pids.append(post.pid)

        return pids
