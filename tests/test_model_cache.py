import os
import random

import numpy as np
import pytest

from sklearn.feature_extraction.text import TfidfVectorizer

print 'in test_model_cache.py'

@pytest.fixture(scope='function')
def model_cache(tmpdir):
    # import things from app in fixture because the session scoped fixture in
    # conftest will run first to confirm that the environment is set up
    # correctly.
    from app.utils import ModelCache
    model_cache = ModelCache(str(tmpdir))
    return model_cache


@pytest.fixture(scope='module')
def dummy_cid():
    ALPHABET = '123456789abcdefghijklmnopqrstuvwxyz'
    cid = ''.join([random.choice(ALPHABET) for i in xrange(14)])
    return cid


@pytest.fixture(scope='module')
def dummy_models():
    dummy_vectorizer = TfidfVectorizer(analyzer='word')
    dummy_matrix = dummy_vectorizer.fit_transform(['this is a test word set',
                                                   'just some random words'])
    dummy_pid_list = np.array([1,2,3,4,5])

    return dummy_vectorizer, dummy_matrix, dummy_pid_list


def test_store_models_happy_case(model_cache, dummy_cid, dummy_models):
    vectorizer, matrix, pid_list = dummy_models

    model_cache.store_model(dummy_cid, 'dummy_model', vectorizer)
    model_cache.store_matrix(dummy_cid, 'dummy_model', matrix)
    model_cache.store_pid_list(dummy_cid, 'dummy_model', pid_list)

    assert os.path.isdir(os.path.join(model_cache.cache_path, dummy_cid))
    assert os.path.isfile(os.path.join(model_cache.cache_path, dummy_cid,
                                       'dummy_model_vectorizer.pkl'))
    assert os.path.isfile(os.path.join(model_cache.cache_path, dummy_cid,
                                       'dummy_model_matrix.npz'))
    assert os.path.isfile(os.path.join(model_cache.cache_path, dummy_cid,
                                       'dummy_model_pid_list.csv'))

def test_get_models_happy_case(model_cache, dummy_cid, dummy_models):
    vectorizer, matrix, pid_list = dummy_models

    model_cache.store_model(dummy_cid, 'dummy_model', vectorizer)
    model_cache.store_matrix(dummy_cid, 'dummy_model', matrix)
    model_cache.store_pid_list(dummy_cid, 'dummy_model', pid_list)

    new_model, new_matrix, new_pid_list = model_cache.get_all(dummy_cid,
                                                              'dummy_model')

    # it is inefficient to check if two sparse matrices are equivalent but you
    # can check if there is not a difference in the number of explicitly stored
    # values
    assert (matrix != new_matrix).nnz == 0
    assert np.array_equal(pid_list, new_pid_list)
