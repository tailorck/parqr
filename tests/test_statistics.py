import pytest
import pandas as pd
import time
import mock

from app.exception import InvalidUsage
from app.statistics import (
    get_unique_users,
    total_posts_in_course,
    number_posts_prevented,
    get_top_attention_warranted_posts
)


@pytest.fixture(scope="module")
def unit_test_posts_df():
    unit_test_posts_df = pd.read_csv('tests/fixtures/unit_test_posts_df.csv')
    return unit_test_posts_df


@pytest.fixture(scope="module")
def unit_test_course_df():
    unit_test_course_df = pd.read_csv('tests/fixtures/unit_test_course_df.csv')
    return unit_test_course_df


@pytest.fixture(scope="module")
def unit_test_events_df():
    unit_test_events_df = pd.read_csv('tests/fixtures/unit_test_events_df.csv')
    return unit_test_events_df


@mock.patch('app.statistics.Course')
@mock.patch('app.statistics.convert_db_course_to_df')
@mock.patch('app.statistics.convert_events_to_df')
@pytest.mark.skip('Disabled due to conversion to mongoengine queries')
def test_get_unique_users(mock_convert_events_to_df,
                          mock_convert_db_course_to_df,
                          mock_Course,
                          unit_test_events_df,
                          unit_test_course_df):
    """
    Unique User Count
        a) Check if the course ID is not valid
        b) Check if the starting time is not valid
        c) Check if the course ID is parsed, but there is no event
           registered for it
        d) Check if in a case, the unique user count is equal to actual
           unique user count
        e) Check in case where there is a null df created after my filtering
           of the events_df

    """

    # Case (a):
    starting_time = 1
    course_id = 'parqrrandomtest'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    mock_Course.objects.return_value = False
    with pytest.raises(InvalidUsage):
        unique_user = get_unique_users(course_id, starting_time)

    mock_Course.objects.return_value = True

    # Case (b):
    current_time = time.time()
    starting_time = current_time + 100000
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    with pytest.raises(InvalidUsage):
        unique_user = get_unique_users(course_id, starting_time)

    '''
    # Disabled due to conversion to mongoengine queries
    # Case (c) and (e):
    starting_time = 0
    course_id = 'jc6w44hrp9v2ki'
    unit_test_events_df_c = unit_test_events_df[unit_test_events_df["course_id"] != 'jc6w44hrp9v2ki']
    mock_convert_events_to_df.return_value = unit_test_events_df_c
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    unique_user = get_unique_users(course_id, starting_time)
    assert unique_user == 0
    '''

    '''
    # Disabled due to conversion to mongoengine queries
    # Case (d):
    course_id = 'jc6w44hrp9v2ki'
    starting_time = 0
    unit_test_events_df_d = unit_test_events_df[unit_test_events_df["course_id"] == 'jc6w44hrp9v2ki']
    mock_convert_events_to_df.return_value = unit_test_events_df_d
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    unique_user = get_unique_users(course_id, starting_time)
    assert unique_user == 55
    '''


@mock.patch('app.statistics.Course')
@mock.patch('app.statistics.convert_db_course_to_df')
@mock.patch('app.statistics.convert_db_posts_to_df')
@pytest.mark.skip('Disabled due to conversion to mongoengine queries')
def test_total_posts_in_course(mock_convert_db_posts_to_df,
                               mock_convert_db_course_to_df,
                               mock_Course,
                               unit_test_course_df,
                               unit_test_posts_df):
    """
    Total posts in a course given a course_id
        a) Check if the course ID is not valid
        b) Check if there are 0 posts for a course
        c) Check if the count of total post for a particular course ID is correct

    """

    # Case (a):
    starting_time = 1
    course_id = 'parqrrandomtest'
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    mock_Course.objects.return_value = False
    with pytest.raises(InvalidUsage):
        total_posts = total_posts_in_course(course_id)

    mock_Course.objects.return_value = True

    # Case (c)
    starting_time = 1
    course_id = 'dummycourse'
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    total_posts = total_posts_in_course(course_id)
    assert total_posts == 0

    # Case (d)
    starting_time = 1
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    total_posts = total_posts_in_course(course_id)
    assert total_posts == 544


@mock.patch('app.statistics.Course')
@mock.patch('app.statistics.convert_events_to_df')
@mock.patch('app.statistics.convert_db_course_to_df')
@mock.patch('app.statistics.convert_db_posts_to_df')
@pytest.mark.skip('Disabled due to conversion to mongoengine queries')
def test_number_posts_prevented(mock_convert_db_posts_to_df,
                                mock_convert_db_course_to_df,
                                mock_convert_events_to_df,
                                mock_Course,
                                unit_test_events_df,
                                unit_test_course_df,
                                unit_test_posts_df):
    """
    Number of posts prevented by use of Parqr
        a) Check if the course ID is not valid
        b) Check if the starting time is not valid
        c) Check if the course ID is parsed, but there is no event
           registered for it
        d) Check if there is null df created after the following filtering:
            - Filter events_df based on course_id and starting time
            - Filter events_df by 'newPost' event and create a new df
            - Filter events_df by 'PostSubmitted' event and create a new df
        e) Check if the posts prevented case is the actual post prevented
           count

    """

    # Case (a)
    starting_time = 1
    course_id = 'parqrrandomtest'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    mock_Course.objects.return_value = False
    with pytest.raises(InvalidUsage):
        num_posts_prevented = number_posts_prevented(course_id, starting_time)

    mock_Course.objects.return_value = True

    # Case (b)
    current_time = time.time()
    starting_time = current_time + 100000
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    with pytest.raises(InvalidUsage):
        num_posts_prevented = number_posts_prevented(course_id, starting_time)

    '''
    # Case (c)
    starting_time = 1
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    num_posts_prevented = number_posts_prevented(course_id, starting_time)
    assert num_posts_prevented == 0
    # This results in: assert 28 == 0
    '''

    # Case (d) Part 1
    current_time = time.time()
    starting_time = current_time - 100
    course_id = 'jc6w44hrp9v2ki'
    unit_test_events_df_d1 = unit_test_events_df[unit_test_events_df["course_id"] != 'jc6w44hrp9v2ki']
    mock_convert_events_to_df.return_value = unit_test_events_df_d1
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    num_posts_prevented = number_posts_prevented(course_id, starting_time)
    assert num_posts_prevented == 0

    # Case (d) Part 2
    starting_time = 1
    course_id = 'jc6w44hrp9v2ki'
    unit_test_events_df_d2 = unit_test_events_df[unit_test_events_df["event"] != 'newPost']
    mock_convert_events_to_df.return_value = unit_test_events_df_d2
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    num_posts_prevented = number_posts_prevented(course_id, starting_time)
    assert num_posts_prevented == 0

    # Case (d) Part 3
    starting_time = 1
    course_id = 'jc6w44hrp9v2ki'
    unit_test_events_df_d3 = unit_test_events_df[unit_test_events_df["event"] != 'postSubmitted']
    mock_convert_events_to_df.return_value = unit_test_events_df_d3
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    num_posts_prevented = number_posts_prevented(course_id, starting_time)
    assert num_posts_prevented == 21

    # Case (e)
    starting_time = 1
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_events_to_df.return_value = unit_test_events_df
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    num_posts_prevented = number_posts_prevented(course_id, starting_time)
    assert num_posts_prevented == 28


@mock.patch('app.statistics.Course')
@mock.patch('app.statistics.convert_db_course_to_df')
@mock.patch('app.statistics.convert_db_posts_to_df')
@pytest.mark.skip('Disabled due to conversion to mongoengine queries')
def test_get_top_attention_warranted_posts(mock_convert_db_posts_to_df,
                                           mock_convert_db_course_to_df,
                                           mock_Course,
                                           unit_test_course_df,
                                           unit_test_posts_df):
    """
    Top posts warranting instructor attention
        a) Check if the course ID is not valid
        b) Check if there is null df created after the following filtering:
            - Filter posts_df based on course_id
            - Filter posts_df based on instructor answer's absence
            - Filter posts_df based on student answer's absence
        c) Check multiple conditions on the cases of getting the best top
           posts for different scenario
    """

    # Case (a)
    number_of_posts = 5
    course_id = 'parqrrandomtest'
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    mock_Course.objects.return_value = False
    with pytest.raises(InvalidUsage):
        top_posts = get_top_attention_warranted_posts(course_id, number_of_posts)

    mock_Course.objects.return_value = True

    # Case (b)
    number_of_posts = 5
    course_id = 'jc6w44hrp9v2ki'
    mock_convert_db_posts_to_df.return_value = unit_test_posts_df
    mock_convert_db_course_to_df.return_value = unit_test_course_df
    top_posts = get_top_attention_warranted_posts(course_id, number_of_posts)
    assert top_posts[4]["post_id"] == 296
    assert top_posts[2]["title"] == 'Assignment 3 Part 1 Discussion: Bayesian Network'
    assert len(top_posts[0]["properties"]) == 5
