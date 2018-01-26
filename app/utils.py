from Crypto.PublicKey import RSA
import re
from os.path import dirname, abspath, join


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


def read_credentials():
    """Method to read encrypted .login file for Piazza username and password"""
    curr_dir = dirname(abspath(__file__))
    key_file = join(curr_dir, '..', '.key.pem')
    login_file = join(curr_dir, '..', '.login')

    with open('.key.pem') as f:
        key = RSA.importKey(f.read())

    with open('.login') as f:
        email_bytes = f.read(128)
        password_bytes = f.read(128)

    return key.decrypt(email_bytes), key.decrypt(password_bytes)
