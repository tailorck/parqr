import torch
from statistics import mean
import torch.nn as nn
from pytorch_lightning.core.lightning import LightningModule
from sklearn.metrics import precision_score, recall_score, f1_score


class BasicNN(LightningModule):
    def __init__(self, input_size, hidden_size=128, output_size=2):
        super().__init__()
        self.h1 = nn.Linear(2 * input_size, hidden_size)
        self.h2 = nn.Linear(hidden_size, output_size)

    def forward(self, q1, q2):
        X = torch.cat((q1, q2), dim=1)
        embedding = nn.functional.relu(self.h1(X))
        return self.h2(embedding), embedding


    def training_step(self, batch, batch_idx):
        q1, q2, y = batch
        y_pred, _ = self.forward(q1, q2)
        loss = nn.functional.cross_entropy(y_pred, y)
        return {"loss": loss}

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.001)

    # def validation_step(self, batch, batch_idx):
    #     q1, q2, y = batch
    #     y_pred, _ = self.forward(q1, q2)
    #     return {'val_loss': nn.functional.cross_entropy(y_pred, y)}

    # def validation_epoch_end(self, outputs):
    #     avg_loss = torch.stack([out['val_loss'] for out in outputs]).mean()
    #     return {'val_loss': avg_loss, 'log': {'val_loss': avg_loss}}

    def test_step(self, batch, batch_idx):
        q1, q2, y = batch
        y_pred, _ = self.forward(q1, q2)
        y_dist = nn.functional.log_softmax(y_pred, dim=1)
        _, ind = torch.max(y_dist, dim=1)
        precision = precision_score(y, ind)
        recall = recall_score(y, ind)
        f1 = f1_score(y, ind)
        return {
            "test_loss": nn.functional.cross_entropy(y_pred, y),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    def test_epoch_end(self, outputs):
        avg_loss = torch.stack([out["test_loss"] for out in outputs]).mean()
        avg_precision = mean([out["precision"] for out in outputs])
        avg_recall = mean([out["recall"] for out in outputs])
        avg_f1 = mean([out["f1"] for out in outputs])
        results = {
            "test_loss": avg_loss,
            "avg_p": avg_precision,
            "avg_r": avg_recall,
            "avg_f1": avg_f1,
        }
        return dict(**results, log=results)


class SiameseNN(LightningModule):
    def __init__(self, input_size, hidden_size=128, output_size=2):
        super().__init__()
        self.W1 = nn.Parameter(torch.rand(hidden_size, input_size))
        self.b1 = nn.Parameter(torch.rand(hidden_size))
        self.W_compare = nn.Parameter(torch.rand(output_size, 3 * hidden_size))

    def forward(self, q1, q2):
        q1 = nn.functional.linear(q1, self.W1, self.b1)
        q2 = nn.functional.linear(q2, self.W1, self.b1)

        total = torch.cat((q1, q2, q1 - q2), dim=1)
        return nn.functional.linear(total, self.W_compare), q1


    def training_step(self, batch, batch_idx):
        q1, q2, y = batch
        y_pred, _ = self.forward(q1, q2)
        loss = nn.functional.cross_entropy(y_pred, y)
        return {'loss': loss}

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.001)

    # def validation_step(self, batch, batch_idx):
    #     q1, q2, y = batch
    #     y_pred, _ = self.forward(q1, q2)
    #     return {'val_loss': nn.functional.cross_entropy(y_pred, y)}

    # def validation_epoch_end(self, outputs):
    #     avg_loss = torch.stack([out['val_loss'] for out in outputs]).mean()
    #     return {'val_loss': avg_loss, 'log': {'val_loss': avg_loss}}

    def test_step(self, batch, batch_idx):
        q1, q2, y = batch
        y_pred, _ = self.forward(q1, q2)
        y_dist = nn.functional.log_softmax(y_pred, dim=1)
        _, ind = torch.max(y_dist, dim=1)
        precision = precision_score(y, ind)
        recall = recall_score(y, ind)
        f1 = f1_score(y, ind)
        return {
            "test_loss": nn.functional.cross_entropy(y_pred, y),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    def test_epoch_end(self, outputs):
        avg_loss = torch.stack([out["test_loss"] for out in outputs]).mean()
        avg_precision = mean([out["precision"] for out in outputs])
        avg_recall = mean([out["recall"] for out in outputs])
        avg_f1 = mean([out["f1"] for out in outputs])
        results = {
            "test_loss": avg_loss,
            "avg_p": avg_precision,
            "avg_r": avg_recall,
            "avg_f1": avg_f1,
        }
        return dict(**results, log=results)