from abc import ABC, abstractmethod

class Dataset(ABC):
    @property
    @abstractmethod
    def train(self):
        """ returns train data and labels
        """
        pass

    @property
    @abstractmethod
    def test(self):
        """ returns test data and labels
        """
        pass
