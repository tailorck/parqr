from abc import ABC, abstractmethod
from typing import Dict, Callable, Any, Union
import numpy as np


class Dataset(ABC):
    @property
    @abstractmethod
    def train(self):
        """ returns train data and labels """
        pass

    @property
    @abstractmethod
    def test(self):
        """ returns test data and labels """
        pass


class Model(ABC):
    @abstractmethod
    def fit(self, X, y):
        pass

    @abstractmethod
    def predict(self, query):
        pass


class Trainer(object):
    def __init__(self, model: Model, dataset: Dataset):
        self._model = model
        self._dataset = dataset

    def run(self):
        train_data, train_scores = self._dataset.train
        self._model.fit(train_data, train_scores)

    def evaluate(self, metrics: Dict[Callable, Dict[str, Any]]) -> Dict[Union[Callable, str], Any]:
        test_data, test_scores = self._dataset.test
        y_pred = self._model.predict(test_data)
        y_pred = np.array([self._dataset._list_to_one_hot(pred) for pred in y_pred])
        results = {}
        for metric, params in metrics.items():
            if "label" in params:
                label = params.pop("label")
            else:
                label = metric.__name__
            results[label] = metric(y_pred, test_scores, **params)
        return results
