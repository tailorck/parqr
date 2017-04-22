import re


def clean(string):
    """Removes all punctuation and numbers from string before converting all
    upper case characters to lower case

    Returns:
        A string without punctuation and numbers with only lowercase letters
    """
    only_letters = re.sub('[^a-zA-Z]', ' ', string)
    return only_letters.lower().strip()


def clean_and_split(string):
    """Removes punctuation and numbers from string before converting all
    characters to lower case and splitting the string into a list

    Retuns:
        A list of the cleaned string
    """
    return clean(string).split()
