from Crypto.PublicKey import RSA
import re
from os.path import dirname, abspath, join


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


def read_credentials():
    curr_dir = dirname(abspath(__file__))
    key_file = join(curr_dir, '..', '.key.pem')
    login_file = join(curr_dir, '..', '.login')

    with open('.key.pem') as f:
        key = RSA.importKey(f.read())

    with open('.login') as f:
        email_bytes = f.read(128)
        password_bytes = f.read(128)

    return key.decrypt(email_bytes), key.decrypt(password_bytes)
