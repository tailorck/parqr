import warnings

import time
import boto3
import numpy as np
import simplejson as json
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

from app.constants import TFIDF_MODELS
from app.model_cache import ModelCache

warnings.filterwarnings("ignore")

STOP_WORDS = set(ENGLISH_STOP_WORDS)
lambda_client = boto3.client('lambda')


class ModelTrain(object):

    def __init__(self, course_id):
        """ModelTrain constructor"""
        self.model_cache = ModelCache()
        self.posts = boto3.resource('dynamodb').Table(course_id)

    def persist_models(self, cid):
        """Vectorizes the information in database into multiple TF-IDF models.
        The models are persisted by pickling the TF-IDF sklearn models,
        storing the sparse vector matrix as a npz file, and saving the
        pid_list for each model as a csv file.

        Args:
            cid: The course id of the class to vectorize
        """
        print('Vectorizing words from course: {}'.format(cid))

        for model in list(TFIDF_MODELS):
            self._create_tfidf_model(cid, model)

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
        words, pid_list = self._get_words_for_model(model_name, cid)
        # print(words, pid_list, words.size)
        if words.size != 0:
            vectorizer = TfidfVectorizer(analyzer='word',
                                         stop_words=STOP_WORDS,
                                         lowercase=True)
            matrix = vectorizer.fit_transform(words)

            self.model_cache.store_model(cid, model_name, vectorizer)
            self.model_cache.store_matrix(cid, model_name, matrix)
            self.model_cache.store_pid_list(cid, model_name, pid_list)

    def _get_words_for_model(self, model_name, cid):
        """Retrieves the appropriate text for a given course and model name.

        Currently there are 4 options for model_names, so the text retrieved
        will be either:
            - The words in the post body, subject, and tags
            - The words in the post student answer
            - The words in the post instructor answer
            - The words in the post followups

        Args:
            model_name (str): The name of the model dictated by the
                TFIDF_MODELS enum

        Returns:
            (tuple): tuple containing:
                words (list): The words associated with the given model name
                model_pid_list (list): The pids associated with each string in
                    the words list
        """
        posts = self._get_all_posts()

        payload = {
            "source": "ModelTrain",
            "posts": posts,
            "model_name": model_name.name,
            "course_id": cid
        }

        start = time.time()
        response = lambda_client.invoke(
            FunctionName='Parqr-Cleaner:PROD',
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(payload), encoding='utf8')
        )
        end = time.time()

        cleaned_posts = json.loads(response['Payload'].read().decode("utf-8"))
        if "words" in cleaned_posts:
            words = cleaned_posts["words"]
            model_pid_list = cleaned_posts["model_pid_list"]
            print("Cleaned {} posts in {} seconds for {}".format(len(model_pid_list), end - start, model_name.name))
        else:
            print(cleaned_posts)
            raise TimeoutError

        return np.array(words), np.array(model_pid_list)

    def _get_all_posts(self) -> list:
        """Retrives all posts for a specific course

        Returns: a list of post objects

        """
        response = self.posts.scan()
        posts = response['Items']

        while 'LastEvaluatedKey' in response:
            response = self.posts.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            posts.extend(response['Items'])

        print(str(len(posts)) + " posts retrieved")
        return posts


def lambda_handler(event, context):
    print(event, context)
    if event.get("course_ids"):
        for course_id in event["course_ids"]:
            mt = ModelTrain(course_id)
            mt.persist_models(course_id)
            print("Course with course_id {}, persisted".format(course_id))
