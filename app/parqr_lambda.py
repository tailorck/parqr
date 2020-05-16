import random
from datetime import datetime, timedelta

import time
import json
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
import boto3

from app.model_cache import ModelCache
from app.constants import (
    TFIDF_MODELS,
    SCORE_THRESHOLD,
    COURSE_MODEL_RELOAD_DELAY_S
)

lambda_client = boto3.client('lambda')


def get_posts_table(course_id):
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table(course_id)


def get_ddb():
    return boto3.client('dynamodb')



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
        self._model_cache = ModelCache()

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
        # Connect to DDB
        payload = {
            "source": "Query",
            "query": query
        }
        print(payload)
        start = time.time()
        response = lambda_client.invoke(
            FunctionName='Parqr-Cleaner:PROD',
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(payload), encoding='utf8')
        )
        print("Cleaned Query in {} ms".format((time.time() - start) * 1000))
        # clean query vector
        clean_query = json.loads(response['Payload'].read().decode("utf-8")).get("clean_query")

        # Retrive the scores for each model in the course as a pandas DataFrame
        tfidf_scores = self._get_tfidf_recommendations(cid, clean_query, N)

        # Take a weighted combination of the scores from each model
        weights = pd.DataFrame([0.4, 0.2, 0.2, 0.2], index=list(TFIDF_MODELS))
        final_scores = tfidf_scores.dot(weights)
        final_scores.columns = ['scores']
        final_scores.sort_values(by=['scores'], ascending=False, inplace=True)

        start_top_posts = time.time()
        # Return post id, subject, and score for the top N scores in the df
        top_pids = [{"post_id": {'N': str(pid)}} for pid in final_scores.index[:N]
                    if final_scores.loc[pid][0] > SCORE_THRESHOLD]

        top_posts = []
        get_items_time = 0
        if len(top_pids) > 0:
            start_get_items = time.time()
            posts = get_ddb()
            responses = posts.batch_get_item(
                RequestItems={
                    cid: {
                        'Keys': top_pids
                    }
                }
            ).get("Responses").get(cid)
            get_items_time = (time.time() - start_get_items) * 1000
            print("Retrieved {} Top Posts from DDB in {} ms"
                  .format(len(responses), get_items_time))

            for post in responses:
                pid = int(post.get("post_id").get("N"))
                score = final_scores.loc[pid][0]
                subject = post.get("subject").get('S')
                s_answer = True if post.get("s_answer") is not None else False
                i_answer = True if post.get("i_answer") is not None else False

                # the modified date
                modified_date = post.get("created").get('N')
                num_unresolved_followups = post.get("num_unresolved_followups", {"N": 0}).get('N')
                followups = post.get("followups", {"L": []}).get('L')
                num_followups = len(followups)
                resolved = True if not num_unresolved_followups else False

                top_posts.append({
                    'pid': pid,
                    'score': score,
                    'subject': subject,
                    's_answer': s_answer,
                    'i_answer': i_answer,
                    'feedback': False,
                    'modified_date': modified_date,
                    'num_followups': num_followups,
                    'resolved': resolved
                })
        print("Generated {} Top Posts in {} ms"
              .format(len(top_posts), (time.time() - start_top_posts) * 1000 - get_items_time))
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
        # all_pids = self._get_all_pids(cid, course)
        now = datetime.now()
        delay = timedelta(seconds=COURSE_MODEL_RELOAD_DELAY_S)

        # If the models for a course are not loaded into memory or it has been
        # some time since they were loaded last, reload them.
        start = time.time()
        if cid not in self._course_dict:
            self._load_all_models(cid)
        elif now - self._course_dict[cid].last_load > delay:
            print('Reloading models for cid: {}'.format(cid))
            self._load_all_models(cid)
        print("Loaded models in {} ms".format((time.time() - start) * 1000))

        start = time.time()
        course_info = self._course_dict[cid]
        all_pids = course_info.models[TFIDF_MODELS.POST].post_ids
        tfidf_scores = pd.DataFrame(index=all_pids)
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
        print("Generated TF-IDF Scores in {} ms".format((time.time() - start) * 1000))
        return tfidf_scores

    def _load_all_models(self, cid):
        """Uses the ModelCache class to load the sklearn model, matrix, and
        post_ids that are stored on disk into memory.

        Args:
            cid (str): The course id of interest
        """
        print("Loading all models for cid: {}".format(cid))

        if cid in self._course_dict:
            course_info = self._course_dict[cid]
        else:
            course_info = CourseInfo(cid)

        for model_name in TFIDF_MODELS:
            skmodel, matrix, pid_list = self._model_cache.get_all(cid, model_name)
            course_info.models[model_name] = ModelInfo(model_name, skmodel,
                                                       matrix, pid_list)

        course_info.last_load = datetime.now()

        if cid not in self._course_dict:
            self._course_dict[cid] = course_info


def lambda_handler(event, context):
    print(event, context)
    start = time.time()
    parqr = Parqr()
    print("Set up Parqr class in {} ms".format((time.time() - start) * 1000))

    body = json.loads(event.get("body"))
    course_id = event['pathParameters'].get("course_id")
    query = body["query"]
    user_id = body.get("user_id")
    if user_id:
        payload = {
            "course_id": course_id,
            "user_id": user_id
        }

        lambda_client.invoke(
            FunctionName='Users',
            InvocationType='Event',
            Payload=bytes(json.dumps(payload), encoding='utf8')
        )

    N = int(body.get("N", 5))
    recs = parqr.get_recommendations(course_id, query, N)
    print(recs)

    if random.random() < 0.1 and recs:
        print("Feedback Requested")
        feedback_payload = {
            "source": "query",
            "course_id": course_id,
            "query": query,
            "similar_posts": recs
        }

        response = lambda_client.invoke(
            FunctionName='Feedbacks',
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(feedback_payload), encoding='utf8')
        )

        recs = json.loads(response['Payload'].read().decode("utf-8")).get("similar_posts")

    return {
        'statusCode': '200',
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Access-Control-Allow-Headers,Access-Control-Allow-Origin,X-Requested-With",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        'body': json.dumps(recs)
    }
