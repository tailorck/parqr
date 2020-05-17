import json
from tqdm import tqdm
import pickle
import re
from itertools import chain

import numpy as np
import pandas as pd
from scipy.sparse import hstack, coo_matrix
import pytorch_lightning as pl
from sklearn.neighbors import KDTree
import torch
import torch.nn as nn
from quora_binary_clf import BasicNN, SiameseNN
from sklearn.feature_extraction.text import TfidfVectorizer
from pytorch_lightning import loggers

import metrics
from base import Dataset, Model, Trainer


class QuoraDataset(Dataset):
    def __init__(self, data_path, train_frac=0.8, data_frac=1.0):
        self._data = pd.read_csv(data_path, delimiter="\t").dropna()
        if data_frac < 1:
            self._data = self._data.groupby("is_duplicate").apply(
                lambda x: x.sample(frac=data_frac)
            )

        train_mask = np.random.rand(self._data.shape[0]) < train_frac
        self._train = self._data.iloc[train_mask]
        self._test = self._data.iloc[~train_mask]

    @property
    def train(self):
        return (
            self._train[["question1", "question2"]],
            self._train["is_duplicate"].values,
        )

    @property
    def test(self):
        return self._test[["question1", "question2"]], self._test["is_duplicate"].values


class BasicModel(Model):
    def __init__(self, **params):
        self._params = params
        self._tfidf = None
        self._net = None
        self._tree = None

    def fit(self, X, y, use_saved=False):
        if use_saved:
            with open("saved_tfidf.pkl", "r") as fp:
                self._tfidf = pickle.load(fp)
            with open("saved_tree.pkl", "r") as fp:
                self._tree = pickle.load(fp)
            self._net = BasicNN.load_from_checkpoint(
                checkpoint_path="saved_model.ckpt",
                input_size=self._tfidf.max_features,
                hidden_size=128,
                output_size=2,
            )
        else:
            # Clean up input and convert to tfidf
            q1, q2 = X["question1"], X["question2"]
            q1 = q1.str.replace(r"[^a-zA-Z]", " ").values.flatten()
            q2 = q2.str.replace(r"[^a-zA-Z]", " ").values.flatten()
            vocab = np.concatenate((q1, q2))
            self._tfidf = TfidfVectorizer(max_features=256).fit(vocab)

            with open("saved_tfidf.pkl", "wb") as fp:
                pickle.dump(self._tfidf, fp)

            # torch expects sparse matrices in coo format
            inp1 = coo_matrix(self._tfidf.transform(q1))
            inp2 = coo_matrix(self._tfidf.transform(q2))

            # switch these around to use basic or siamese net
            # all models live in quora_binary_clf.py
            self._net = BasicNN(self._tfidf.max_features, self._tfidf.max_features)
            # self._net = SiameseNN(self._tfidf.max_features)

            # each forward pass of our networks accepts batches of questions separately
            inp1_tensor = torch.sparse.FloatTensor(
                torch.LongTensor(np.vstack((inp1.row, inp1.col))),
                torch.FloatTensor(inp1.data),
                torch.Size(inp1.shape),
            )
            inp2_tensor = torch.sparse.FloatTensor(
                torch.LongTensor(np.vstack((inp2.row, inp2.col))),
                torch.FloatTensor(inp2.data),
                torch.Size(inp2.shape),
            )

            train_dataset = torch.utils.data.TensorDataset(
                inp1_tensor, inp2_tensor, torch.LongTensor(y)
            )
            train_len = int(0.8 * len(train_dataset))
            val_len = len(train_dataset) - train_len
            train_dataset, val_dataset = torch.utils.data.random_split(
                train_dataset, lengths=[train_len, val_len]
            )

            train_dataloader = torch.utils.data.DataLoader(
                train_dataset, batch_size=32, num_workers=0, shuffle=True
            )
            val_dataloader = torch.utils.data.DataLoader(
                val_dataset, batch_size=32, num_workers=0, shuffle=False
            )

            # train and test model
            tb_logger = loggers.TensorBoardLogger("logs/")
            pl_trainer = pl.Trainer(max_epochs=1, weights_summary=None, logger=tb_logger)
            pl_trainer.fit(self._net, train_dataloader)  # , val_dataloader)
            pl_trainer.save_checkpoint("saved_model.ckpt")
            # NOTE at the moment val_dataset/loader is being used as a test set
            pl_trainer.test(self._net, test_dataloaders=val_dataloader)

            # build KDtree from hidden layer of the trained model
            # NOTE everything after this point isn't being used for now

            # embeddings = []
            # self._net.eval()
            # for q1, q2, _ in train_dataset:
            #     _, embedding = self._net(
            #         q1.to_dense().view(1, -1), q2.to_dense().view(1, -1)
            #     )
            #     embeddings.append(embedding.detach().numpy().flatten())

            # self._tree = KDTree(np.stack(embeddings, axis=0))

            # with open("saved_tree.pkl", "wb") as fp:
            #     pickle.dump(self._tree, fp)

    def predict(self, X):
        if self._tfidf is None or self._net is None or self._tree is None:
            raise ValueError("Model should be .fit() first")
        X = self._tfidf.transform(X).toarray()
        ind, dist = self._tree.query_radius(
            X, r=1, return_distance=True, sort_results=True
        )
        return list(ind)


if __name__ == "__main__":
    # NOTE the data_frac set here does matter right now, even for our current testing
    data = QuoraDataset("datasets/data.tsv", train_frac=0.8, data_frac=0.25)
    rank_model = BasicModel()
    clf = Trainer(rank_model, data)
    clf.run()
    # NOTE we aren't using our metrics for now
    # results = clf.evaluate(
    #     metrics={
    #         metrics.precision_at_k: {"label": "P@5"},
    #         metrics.recall_at_k: {"label": "R@5"},
    #         # metrics.mean_average_precision: {"label": "MAP"},
    #         metrics.discounted_cumulative_gain: {"label": "dcgn", "normalize": True},
    #     }
    # )
    # for label, result in results.items():
    #     print(f"{label}:  :: {np.nanmean(result)}")
