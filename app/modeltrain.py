from multiprocessing.dummy import Pool
from functools import partial
from threading import Thread
import logging

import numpy as np
from sklearn.feature_extraction import text

from app.exception import InvalidUsage
from constants import TFIDF_MODELS
from models import Post, Course
from utils import clean_and_split, stringify_followups, ModelCache


class ModelTrain(object):

    def __init__(self, verbose=False):
        """ModelTrain constructor

        Args:
            verbose (bool): A bool denoting if the module will print info msgs
        """
        # TODO: remove hard coded resources path.
        # Requires getting setup.py working and then use pkg_resources
        self.verbose = verbose
        self.model_cache = ModelCache('app/resources')
        self.logger = logging.getLogger('app')
        self._threads = {}

    def persist_all_models(self):
        """Creates new models for each course in database and persists each to
        file"""
        for course in Course.objects():
            self.persist_model(course.cid)

    def persist_model(self, cid):
        """Creates new models for course with given cid

        Args:
            cid (str): The course id of interest
        """
        if cid in self._threads and self._threads[cid].is_alive():
            raise InvalidUsage('Background thread is running', 500)

        self._threads[cid] = Thread(target=self._persist_model, args=(cid,))
        self._threads[cid].start()

    def _persist_model(self, cid):
        """Vectorizes the information in database into multiple TF-IDF models.
        The models are persisted by pickling the TF-IDF sklearn models,
        storing the sparse vector matrix as a npz file, and saving the
        pid_list for each model as a csv file.

        Args:
            cid: The course id of the class to vectorize
        """
        # TODO: Catch invalid cid
        self.logger.info('Vectorizing words from course: {}'.format(cid))

        pool = Pool(4)
        partial_func = partial(self._create_tfidf_model, cid)
        pool.map(partial_func, list(TFIDF_MODELS))
        pool.close()

    def _create_tfidf_model(self, cid, model_name):
        """Creates a new TfidfVectorizer model from the relevant text in course
        with given course id

        Right now there are only 4 TFIDF models that are being used so the
        function will check which model_name was used and create a new
        vectorizer from the words in either the post body, student answers,
        instructor answers, or followups from each post in the course.

        Args:
            cid (str): The course id of interest
            model_name (str): The name of the model dictated by the
                TFIDF_MODELS enum
        """
        stop_words = set(text.ENGLISH_STOP_WORDS)
        words, pid_list = self._get_words_for_model(cid, model_name)

        if words.size != 0:
            vectorizer = text.TfidfVectorizer(analyzer='word',
                                              stop_words=stop_words)
            matrix = vectorizer.fit_transform(words)

            self.model_cache.store_model(cid, model_name, vectorizer)
            self.model_cache.store_matrix(cid, model_name, matrix)
            self.model_cache.store_pid_list(cid, model_name, pid_list)

    def _get_words_for_model(self, cid, model_name):
        """Retrieves the appropriate text for a given course and model name.

        Currently there are 4 options for model_names, so the text retrieved
        will be either:
            - The words in the post body, subject, and tags
            - The words in the post student answer
            - The words in the post instructor answer
            - The words in the post followups

        Args:
            cid (str): The course id of the course in interest
            model_name (str): The name of the model dictated by the
                TFIDF_MODELS enum

        Returns:
            (tuple): tuple containing:
                words (list): The words associated with the given model name
                model_pid_list (list): The pids associated with each string in
                    the words list
        """
        words = []
        model_pid_list = []

        for post in Post.objects(cid=cid):
            if model_name == TFIDF_MODELS.POST:
                clean_subject = clean_and_split(post.subject)
                clean_body = clean_and_split(post.body)
                tags = post.tags
                words.append(' '.join(clean_subject + clean_body + tags))
                model_pid_list.append(post.pid)
            elif model_name == TFIDF_MODELS.I_ANSWER:
                if post.i_answer:
                    words.append(' '.join(clean_and_split(post.i_answer)))
                    model_pid_list.append(post.pid)
            elif model_name == TFIDF_MODELS.S_ANSWER:
                if post.s_answer:
                    words.append(' '.join(clean_and_split(post.s_answer)))
                    model_pid_list.append(post.pid)
            elif model_name == TFIDF_MODELS.FOLLOWUP:
                if post.followups:
                    followup_str = stringify_followups(post.followups)
                    words.append(' '.join(clean_and_split(followup_str)))
                    model_pid_list.append(post.pid)

        return np.array(words), np.array(model_pid_list)
