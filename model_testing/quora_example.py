import json
import re
from typing import Dict, Union, Callable, Any

import numpy as np
import pandas as pd
from scipy.sparse import lil_matrix, vstack
from sklearn.neighbors import KDTree
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelBinarizer

import base
import metrics


class QuoraDataset(base.Dataset):

    def __init__(self, data_path, train_frac=0.8, data_frac=1.0):

        with open(data_path, "r") as fp:
            self._data = pd.DataFrame(json.load(fp)).dropna()

        self._data_size = self._data.shape[0]

        if data_frac < 1:
            self._data["matches"] = self._data["labels"].apply(lambda x: len(x))
            groups = self._data.groupby("matches")
            self._data = groups.apply(lambda x: x.sample(frac=data_frac))
            self._data.index = self._data.index.droplevel()

        # one_hot = np.stack(self._data["labels"].apply(lambda l: self._list_to_one_hot(l)))
        self._data = self._data.reset_index()

        train_mask = np.random.rand(self._data.shape[0]) < train_frac
        self._X_train = self._data["question"].iloc[train_mask]
        self._X_test = self._data["question"].iloc[~train_mask]
        self._y_train = self._data["labels"][train_mask]
        self._y_test = self._data["labels"][~train_mask]

    def _list_to_one_hot(self, _list):
        zeros = np.zeros(self._data_size)

        if len(_list) > 0:
            zeros[_list] = 1

        return zeros

    @property
    def train(self):
        return self._X_train, self._y_train

    @property
    def test(self):
        return self._X_test, self._y_test


class Trainer(object):

    def __init__(self, model: base.Model, dataset: base.Dataset):
        self._model = model
        self._dataset = dataset

    def run(self):
        train_data, train_scores = self._dataset.train
        self._model.fit(train_data, train_scores)

    def evaluate(self, metrics: Dict[Callable, Dict[str, Any]]) -> Dict[Union[Callable, str], Any]:
        test_data, test_scores = self._dataset.test
        y_pred = self._model.predict(test_data)
        # y_pred = np.array([self._dataset._list_to_one_hot(pred) for pred in y_pred])
        results = {}
        for metric, params in metrics.items():
            if "label" in params:
                label = params.pop("label")
            else:
                label = metric.__name__
            results[label] = metric(y_pred, test_scores, **params)
        return results


class BasicModel(base.Model):

    def __init__(self, **params):
        self._model_params = params

    def _fit_tfidf(self, X):
        vocab = X.values.flatten()
        return TfidfVectorizer(max_features=512).fit(vocab)

    def fit(self, X, y):
        # X = X.apply(self._clean_query)
        X = X.str.replace(r"[^a-zA-Z]", " ")
        self._tfidf = self._fit_tfidf(X)
        self._model = KDTree(self._tfidf.transform(X).toarray(), **self._model_params)

    def predict(self, query):
        query = self._tfidf.transform(query).toarray()
        ind, dist = self._model.query_radius(
            query, r=0.5, return_distance=True, sort_results=True
        )
        return ind


if __name__ == "__main__":
    print("Building dataset")
    dataset = QuoraDataset("datasets/small_query_pair.json")
    print("Train samples: ", dataset.train[0].shape[0])
    print("Test samples: ", dataset.test[0].shape[0])
    rank_model = BasicModel()
    print("Running trainer")
    import pdb; pdb.set_trace()
    clf = Trainer(rank_model, dataset)
    clf.run()
    results = clf.evaluate(
        metrics={
            # metrics.precision_at_k: {"label": "P@5"},
            metrics.recall_at_k: {"label": "R@5"},
            # metrics.discounted_cumulative_gain: {"label": "dcgn", "normalize": True},
        }
    )
    for label, result in results.items():
        print(f"{label}:  :: {np.nanmean(result)}")
