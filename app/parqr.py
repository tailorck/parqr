from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction import text
from app.exception import InvalidUsage
from app.models import Course, Post
from app.utils import clean, clean_and_split
import numpy as np
import logging
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

    def get_similar_posts(self, cid, query, N):
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

        # retrieve the appropriate vectorizer and pre-computed TF-IDF Matrix
        # for this course, or create new ones if they do not exist
        if cid not in self._vectorizers or cid not in self._matrices:
            vectorizer, tfidf_matrix = self._vectorize_words(cid)
        else:
            vectorizer = self._vectorizers[cid]
            tfidf_matrix = self._matrices[cid]

        # the transform method takes an iterable as input. Tthe string does not
        # need to be tokenized, just placed in a list
        q_vector = vectorizer.transform([clean_query])

        # calculate the similarity score for query with all vectors in matrix
        scores = cosine_similarity(q_vector, tfidf_matrix)[0]

        # retrieve the index of the vectors with the highest similarity.
        # np.argsort naturally sorts in ascending order, so the list must be
        # reversed and the top N most similar posts are stored
        top_N_vector_indices = np.argsort(scores)[::-1][:N]

        # the index of the vector in the matrix does not directly correspond to
        # the pid of the associated post, so the vector indices must be mapped
        # to course post ids
        top_N_pids = self._post_ids[cid][top_N_vector_indices]

        # Return post id, subject, and score
        top_posts = {}
        for pid, score in zip(top_N_pids, scores[top_N_vector_indices]):
            post = Post.objects(cid=cid, pid=pid)[0]
            subject = post.subject
            student_answer = True if post.s_answer != None else False
            instructor_answer = True if post.i_answer != None else False
            if  score > constants.THRESHOLD_SCORE:
                top_posts[score] = {'pid': pid,
                                    'subject': subject,
                                    's_answer': student_answer,
                                    'i_answer': instructor_answer}

        return top_posts

    def _get_posts_as_words(self, cid):
        """Queries database for all posts within particular course

        Parameters
        ----------
        cid : str
            The course id of the class found in the url

        Returns
        -------
        words : np.array
            A list of all the words found in the subject, body, and tags of
            each post in the course.
        """
        # TODO: Catch DoesNotExist exception for missing course
        course = Course.objects.get(cid=cid)

        words = []
        pids = []
        for post in course.posts:
            pids.append(post.pid)
            clean_subject = clean_and_split(post.subject)
            clean_body = clean_and_split(post.body)
            tags = post.tags
            words.append(' '.join(clean_subject + clean_body + tags))

        self._post_ids[cid] = np.array(pids)
        return np.array(words)

    def _vectorize_words(self, cid):
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
        stop_words = set(text.ENGLISH_STOP_WORDS)
        vectorizer = text.TfidfVectorizer(analyzer='word',
                                          stop_words=stop_words)

        post_words = self._get_posts_as_words(cid)
        tfidf_matrix = vectorizer.fit_transform(post_words)

        self._vectorizers[cid] = vectorizer
        self._matrices[cid] = tfidf_matrix

        if self.verbose:
            self._logger.info('Finished Vectorizing')

        return vectorizer, tfidf_matrix
