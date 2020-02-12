from abc import ABC, abstractmethod

class Dataset(ABC):
    @abstractmethod
    @property
    def train(self):
        """ returns train data and labels
        """
        pass

    @abstractmethod
    @property
    def test(self):
        """ returns test data and labels
        """
        pass
