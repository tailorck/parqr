import logging
import warnings

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

from app.constants import TFIDF_MODELS
from app.models.course import Course
from app.models.post import Post
from app.exception import InvalidUsage
from app.utils import (
    spacy_clean,
    stringify_followups,
    ModelCache
)

warnings.filterwarnings("ignore")

logger = logging.getLogger('app')

STOP_WORDS = set(ENGLISH_STOP_WORDS)


class ModelTrain(object):

    def __init__(self):
        """ModelTrain constructor"""
        self.model_cache = ModelCache()

    def persist_all_models(self):
        """Creates new models for each course in database and persists each to
        file"""
        for course in Course.objects():
            self.persist_models(course.course_id)

    def persist_models(self, cid):
        """Vectorizes the information in database into multiple TF-IDF models.
        The models are persisted by pickling the TF-IDF sklearn models,
        storing the sparse vector matrix as a npz file, and saving the
        pid_list for each model as a csv file.

        Args:
            cid: The course id of the class to vectorize
        """
        if not Course.objects(course_id=cid):
            raise InvalidUsage('Invalid course id provided')

        logger.info('Training models for course: {}'.format(cid))

        for model in list(TFIDF_MODELS):
            self._create_tfidf_model(cid, model)

        logger.info('Completed training models for course: {}'.format(cid))

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
        words, pid_list = self._get_words_for_model(cid, model_name)

        if words.size != 0:
            vectorizer = TfidfVectorizer(analyzer='word',
                                         stop_words=STOP_WORDS,
                                         lowercase=True)
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

        for post in Post.objects(course_id=cid):
            if model_name == TFIDF_MODELS.POST:
                clean_subject = spacy_clean(post.subject)
                clean_body = spacy_clean(post.body)
                tags = post.tags
                words.append(' '.join(clean_subject + clean_body + tags))
                model_pid_list.append(post.post_id)
            elif model_name == TFIDF_MODELS.I_ANSWER:
                if post.i_answer:
                    words.append(' '.join(spacy_clean(post.i_answer)))
                    model_pid_list.append(post.post_id)
            elif model_name == TFIDF_MODELS.S_ANSWER:
                if post.s_answer:
                    words.append(' '.join(spacy_clean(post.s_answer)))
                    model_pid_list.append(post.post_id)
            elif model_name == TFIDF_MODELS.FOLLOWUP:
                if post.followups:
                    followup_str = stringify_followups(post.followups)
                    words.append(' '.join(spacy_clean(followup_str)))
                    model_pid_list.append(post.post_id)

        return np.array(words), np.array(model_pid_list)
