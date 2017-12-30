from functools import partial
from multiprocessing.dummy import Pool
import logging

import numpy as np
from sklearn.feature_extraction import text

from app.constants import TFIDF_MODELS
from app.models import Post, Course
from app.utils import clean_and_split, stringify_followups, ModelCache


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

    def persist_models(self, cid):
        """Vectorizes the information in database into multiple TF-IDF models.
        The models are persisted by pickling the TF-IDF sklearn models,
        storing the sparse vector matrix as a npz file, and saving the
        pid_list for each model as a csv file.

        Args:
            cid: The course id of the class to vectorize
        """
        self.logger.info('Vectorizing words from course: {}'.format(cid))

        pool = Pool(4)
        partial_func = partial(self._create_tfidf_model, cid)
        pool.map(partial_func, list(TFIDF_MODELS))
        pool.close()

    def _create_tfidf_model(self, cid, model_name):
        """

        Args:
            cid:
            model:

        Returns:

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

    def _get_words_for_model(self, cid, model):
        """

        Args:
            cid:
            model:

        Returns:

        """
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

        return np.array(words), np.array(model_pid_list)


if __name__ == "__main__":
    modeltrain = ModelTrain()
    for course in Course.objects():
        modeltrain.persist_models(course.cid)
