import json
import re

import numpy as np
import pandas as pd
from scipy.sparse import lil_matrix, vstack
from sklearn.neighbors import KDTree
from sklearn.feature_extraction.text import TfidfVectorizer

from src import dataset, metrics, model


class QuoraDataset(dataset.Dataset):
    def __init__(self, data_path, train_frac=0.8, data_frac=1.0):
        with open(data_path, "r") as fp:
            self._data = pd.DataFrame(json.loads(fp.read())).dropna()
        if data_frac < 1:
            self._data = self._data.groupby(lambda r: len(self._data.loc[r, 'labels']) > 0).apply(lambda x: x.sample(frac=data_frac))
        self._data["one_hot"] = self._data["labels"].apply(self._list_to_labels)

        train_mask = np.random.rand(self._data.shape[0]) < train_frac
        self._train = self._data.iloc[train_mask]
        self._test = self._data.iloc[~train_mask]

    def _list_to_labels(self, l):
        arr = lil_matrix((1, self._data.shape[0]), dtype=np.int8)
        l = [i for i in l if i < self._data.shape[0]]
        arr[:, l] = 1
        return arr

    @property
    def train(self):
        return self._train["question"], vstack(self._train["one_hot"].values).toarray()

    @property
    def test(self):
        return self._test["question"], vstack(self._test["one_hot"].values).toarray()


class BasicModel(model.Model):
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
        import pdb; pdb.set_trace()
        ind, dist = self._model.query_radius(query, r=0.5, return_distance=True, sort_results=True)
        return list(ind)


if __name__ == "__main__":
    print("Building dataset")
    dataset = QuoraDataset("./example/Quora_query_pairs.json", data_frac=0.01)
    print("Train samples: ", dataset.train[0].shape[0])
    print("Test samples: ", dataset.test[0].shape[0])
    rank_model = BasicModel()
    print("Running trainer")
    clf = model.Trainer(rank_model, dataset)
    clf.run()
    results = clf.evaluate(
        metrics={
            metrics.precision_at_k: {"label": "P@5"},
            metrics.recall_at_k: {"label": "R@5"},
            metrics.mean_average_precision: {"label": "MAP"},
            # metrics.discounted_cumulative_gain: {"label": "dcgn"},
        }
    )
    for label, result in results.items():
        print(f'{label}: {result} :: {np.nanmean(result)}')
