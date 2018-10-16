import pytest

from app.utils import clean, clean_and_split, stringify_followups


def test_clean():
    # Test Case with Punctuations and trailing spaces
    str_ = "[string. With*, Punctuation!  "
    clean_res = clean(str_)
    expected_res = "string with punctuation"
    assert clean_res == expected_res

    # Test case with numeric values
    str_ = "22 str8ing -10 With 37.256 Numbers"
    clean_res = clean(str_)
    expected_res = "string with numbers"
    assert clean_res == expected_res

    # Test case with upper and lowe cases and trailing spaces
    str_ = "   sTriNg wITh   UPPER AnD  lower Cases"
    clean_res = clean(str_)
    expected_res = "string with upper and lower cases"
    assert clean_res == expected_res

    # Test Case with punctuations, numeric values and trailing spaces
    str_ = "  @<string's>;. (#{176With+_%}&. " \
           "[\$,] |/22Punctuation:=~890| )^?**!"
    clean_res = clean(str_)
    expected_res = "strings with punctuation"
    assert clean_res == expected_res

    # Test Case with newlines in the middle of sentence
    str_ = "strings with\npunctuation"
    clean_res = clean(str_)
    expected_res = "strings with punctuation"
    assert clean_res == expected_res


def test_clean_and_split():
    # Test Case with Punctuations and trailing spaces
    str = "[string. With*, Punctuation!  "
    clean_res = clean_and_split(str)
    expected_res = ["string", "with", "punctuation"]
    assert clean_res == expected_res

    # Test case with numeric values
    str = "22 str8ing -10 With 37.256 Numbers"
    clean_res = clean_and_split(str)
    expected_res = ["string", "with", "numbers"]
    assert clean_res == expected_res

    # Test case with upper and lowe cases and trailing spaces
    str = "   sTriNg wITh   UPPER AnD  lower Cases"
    clean_res = clean_and_split(str)
    expected_res = ["string", "with", "upper", "and", "lower", "cases"]
    assert clean_res == expected_res

    # Test Case with punctuations, numeric values and trailing spaces
    str = "  @<string's>;. (#{176With+_%}&. " \
          "[\$,] |/22Punctuation:=~890| )^?**!"
    clean_res = clean_and_split(str)
    expected_res = ["strings", "with", "punctuation"]
    assert clean_res == expected_res


def test_stringify_followups():

    followup_list = []
    followup = {}
    followup['text'] = 'thank you'
    followup['responses'] = ['you are welcome',
                             'great discussion', 'I ve a better idea now']
    followup_list.append(followup)
    stringify_res = stringify_followups(followup_list)
    expected_res = 'thank you you are welcome great discussion ' \
                   'I ve a better idea now'
    assert stringify_res == expected_res
