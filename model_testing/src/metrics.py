import numpy as np


# recall at k
# dcgain


def recall_at_k(rank_pred, y_true: np.ndarray, k: int = 5) -> np.ndarray:
    """
    Parameters
    ----------
    rank_pred: np.ndarray[int] shape (n_queries, n_returned)
        list of ids giving the predicted ranking of the documents
    y_true: np.ndarray[int8] shape (n_queries, n_documents)
        list of ground truth scores for documents. y_true[i, j] > 0 iff document j is relevant to query i
    k: int
        number of retrieved documents to use

    Returns
    -------
    np.ndarray[float] shape (n_queries,)
        recall at k for each query
    """
    y_true[y_true > 0] = 1
    if isinstance(rank_pred, np.ndarray):
        n_relevant = y_true.sum(axis=1, keepdims=True)
        k = min(rank_pred.shape[1], k)
        recall = (
            y_true[np.arange(y_true.shape[0]).reshape(-1, 1), rank_pred[:, :k]].sum(
                axis=1
            )
            / n_relevant
        )
    else:
        recall = np.empty(len(rank_pred))
        for i, (pred, true_labeling) in enumerate(zip(rank_pred, y_true)):
            k_i = min(len(pred), k)
            n_relevant = true_labeling.sum()
            recall[i] = true_labeling[pred[:k_i]].sum() / n_relevant
    return recall


def precision_at_k(rank_pred, y_true: np.ndarray, k: int = 5) -> np.ndarray:
    """
    Parameters
    ----------
    rank_pred: np.ndarray[int] shape (n_queries, n_returned) or list of ndarrays
        list of ids giving the predicted ranking of the documents
    y_true: np.ndarray[int8] shape (n_queries, n_documents)
        list of ground truth scores for documents. y_true[i] > 0 iff document i is relevant to the query
    k: int
        number of retrieved documents to use

    Returns
    -------
    np.ndarray[float] shape (n_queries,)
        precision at k for each query
    """
    y_true[y_true > 0] = 1
    if isinstance(rank_pred, np.ndarray):
        k = min(rank_pred.shape[1], k)
        precision = (
            y_true[np.arange(y_true.shape[0]).reshape(-1, 1), rank_pred[:, :k]].sum(
                axis=1
            )
            / k
        )
    else:
        precision = np.empty(len(rank_pred))
        for i, (pred, true_labeling) in enumerate(zip(rank_pred, y_true)):
            k_i = min(len(pred), k)
            precision[i] = true_labeling[pred[:k_i]].sum() / k_i

    return precision


def mean_average_precision(rank_pred, y_true: np.ndarray) -> float:
    """
    Parameters
    ----------
    rank_pred: np.ndarray[int] shape (n_queries, n_returned)
        sequence of ids giving the predicted ranking of the documents
    y_true: np.ndarray[int8] shape (n_queries, n_documents)
        list of ground truth scores for documents. y_true[i] > 0 iff document i is relevant to the query

    Returns
    -------
    float
        average precision over 1..k for all queries

    """
    y_true[y_true > 1] = 1
    n_relevant = y_true.sum(axis=1)
    Q = len(rank_pred)
    average_precision = np.zeros((Q,))

    for q in range(Q):
        for k in range(1, min(rank_pred[q].shape[0], n_relevant[q]) + 1):
            average_precision[q] += precision_at_k(
                rank_pred[q].reshape(1, -1), y_true[q].reshape(1, -1), k=k
            )
    return np.nanmean(average_precision / n_relevant)


def discounted_cumulative_gain(
    rank_pred: np.ndarray,
    true_scores: np.ndarray,
    k: int = 5,
    discount: float = 0.8,
    normalize: bool = False,
) -> np.ndarray:
    if isinstance(rank_pred, np.ndarray):
        scores = true_scores[
            np.arange(true_scores.shape[0]).reshape(-1, 1), rank_pred[:, :k]
        ]
        weights = (discount ** np.arange(k)).reshape(1, -1)
        dcgn = np.sum(scores * weights, axis=1)

        if normalize:
            best_ranking = true_scores.sort(axis=1)[:, :k]
            best_dcgn = np.sum(best_ranking * weights, axis=1)
            dcgn = dcgn / best_dcgn

    else:
        dcgn = np.empty(len(rank_pred))
        for i, (pred, scores) in enumerate(zip(rank_pred, true_scores)):
            weights = discount ** np.arange(k)
            dcgn[i] = np.sum(scores[: min(k, len(pred))] * weights[: min(k, len(pred))])
            if normalize:
                best_ranking = np.sort(scores)[:k]
                best_dcgn = np.sum(best_ranking * weights)
                dcgn[i] /= best_dcgn

    return dcgn
