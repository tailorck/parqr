import logging
import re

logger = logging.getLogger('app')


def clean(string):
    """Cleans an input string of nonessential characters for TF-IDF

    Removes all punctuation and numbers from string before converting all upper
    case characters to lower case

    Parameters
    ----------
    string : str
        The input string that needs cleaning

    Returns
    -------
    cleaned_string : str
        The cleaned version of input string
    """
    only_letters = re.sub('[^a-zA-Z]', ' ', string)
    cleaned_string = only_letters.lower().strip()
    return cleaned_string


def clean_and_split(string):
    """Cleans an input string of nonessential characters and converts to list

    Parameters
    ----------
    string : str
        The input string that needs cleaning

    Returns
    -------
    split_string : str
        The cleaned string split up into a list by whitespace
    """
    return clean(string).split()


def stringify_followups(followup_list):
    return_list = []
    for followup in followup_list:
        return_list.append(followup['text'])
        return_list += followup['responses']

    return ' '.join(return_list)
