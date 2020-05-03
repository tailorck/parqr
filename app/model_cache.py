import pickle
import os.path
import boto3
import botocore


class ModelCache(object):
    tmp = '/tmp/'
    model_key_format = '{}_{}_vectorizer.pkl'
    matrix_key_format = '{}_{}_matrix.pkl'
    pid_list_key_format = '{}_{}_pid_list.pkl'

    def __init__(self):
        self.s3 = boto3.client('s3')

    def store_model(self, cid, name, model):
        key = self.model_key_format.format(cid, name)
        self.s3.put_object(
            Bucket="parqr-models",
            Key=key,
            Body=pickle.dumps(model)
        )

    def store_matrix(self, cid, name, matrix):
        key = self.matrix_key_format.format(cid, name)
        self.s3.put_object(
            Bucket="parqr-models",
            Key=key,
            Body=pickle.dumps(matrix)
        )

    def store_pid_list(self, cid, name, pid_list):
        key = self.pid_list_key_format.format(cid, name)
        self.s3.put_object(
            Bucket="parqr-models",
            Key=key,
            Body=pickle.dumps(pid_list)
        )

    def get_all(self, cid, name):
        model = self.get_model(cid, name)
        matrix = self.get_matrix(cid, name)
        pid_list = self.get_pid_list(cid, name)

        return model, matrix, pid_list

    def get_model(self, cid, name):
        key = self.model_key_format.format(cid, name)

        if os.path.exists(self.tmp + key):
            print("Loading model found in /tmp")
            with open(self.tmp + key, "rb") as input_file:
                model = pickle.load(input_file)
        else:
            try:
                self.s3.download_file("parqr-models", key, self.tmp + key)
            except botocore.exceptions.ClientError as e:
                print("Could not find MODEL for cid '{}' with "
                      "name '{}'".format(cid, name))
                model = None
            else:
                print("Downloaded model from s3")
                with open(self.tmp + key, "rb") as input_file:
                    model = pickle.load(input_file)

        return model

    def get_matrix(self, cid, name):
        key = self.matrix_key_format.format(cid, name)

        if os.path.exists(self.tmp + key):
            print("Loading matrix found in /tmp")
            with open(self.tmp + key, "rb") as input_file:
                matrix = pickle.load(input_file)
        else:
            try:
                self.s3.download_file("parqr-models", key, self.tmp + key)
            except botocore.exceptions.ClientError as e:
                print("Could not find MODEL for cid '{}' with "
                      "name '{}'".format(cid, name))
                matrix = None
            else:
                print("Downloaded matrix from s3")
                with open(self.tmp + key, "rb") as input_file:
                    matrix = pickle.load(input_file)
        return matrix

    def get_pid_list(self, cid, name):
        key = self.pid_list_key_format.format(cid, name)
        if os.path.exists(self.tmp + key):
            print("Loading pid_list found in /tmp")
            with open(self.tmp + key, "rb") as input_file:
                pid_list = pickle.load(input_file)
        else:
            try:
                self.s3.download_file("parqr-models", key, self.tmp + key)
            except botocore.exceptions.ClientError as e:
                print("Could not find MODEL for cid '{}' with "
                      "name '{}'".format(cid, name))
                pid_list = None
            else:
                print("Downloaded pid_list from s3")
                with open(self.tmp + key, "rb") as input_file:
                    pid_list = pickle.load(input_file)
        return pid_list
