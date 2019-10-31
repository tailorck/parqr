import pickle
import random
import os

from mock import patch
import numpy as np
import pytest
import scipy

from sklearn.feature_extraction.text import TfidfVectorizer


@pytest.fixture(scope='function')
def model_cache(tmpdir):
    # import things from app in fixture because the session scoped fixture in
    # conftest will run first to confirm that the environment is set up
    # correctly.
    from app.utils import ModelCache
    model_cache = ModelCache()
    return model_cache


@pytest.fixture(scope='module')
def dummy_cid():
    ALPHABET = '123456789abcdefghijklmnopqrstuvwxyz'
    cid = ''.join([random.choice(ALPHABET) for i in range(14)])
    return cid


@pytest.fixture(scope='module')
def dummy_models():
    dummy_vectorizer = TfidfVectorizer(analyzer='word')
    dummy_matrix = dummy_vectorizer.fit_transform(['this is a test word set',
                                                   'just some random words'])
    dummy_pid_list = np.array([1, 2, 3, 4, 5])

    return dummy_vectorizer, dummy_matrix, dummy_pid_list


@patch('app.utils.model_cache.redis')
def test_store_models_happy_case(mock_redis, model_cache, dummy_cid, dummy_models):
    vectorizer, matrix, pid_list = dummy_models

    model_cache.store_model(dummy_cid, 'dummy_model', vectorizer)
    model_cache.store_matrix(dummy_cid, 'dummy_model', matrix)
    model_cache.store_pid_list(dummy_cid, 'dummy_model', pid_list)

    mock_redis.set.call_count == 3
    call_args_list = mock_redis.call_args_list

    for call_args in call_args_list:
        assert cid in call_args[0]
        assert isinstance(call_args[1], str)


@patch('app.utils.model_cache.redis')
def test_get_models_happy_case(mock_redis, model_cache, dummy_cid, dummy_models):
    vectorizer, matrix, pid_list = dummy_models
    mock_redis.get.side_effect = [pickle.dumps(vectorizer),
                                  pickle.dumps(matrix),
                                  pickle.dumps(pid_list)]
    mock_redis.exists.return_value = True
    new_model, new_matrix, new_pid_list = model_cache.get_all(dummy_cid,
                                                              'dummy_model')

    assert mock_redis.get.call_count == 3
    assert isinstance(new_model, TfidfVectorizer)
    assert isinstance(new_matrix, scipy.sparse.csr_matrix)
    assert isinstance(new_pid_list, np.ndarray)