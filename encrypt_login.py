"""
This module creates a key pair to encrypt your Piazza username and password.
The scraper with read the .login file created and decrypt the username and
password with the private key saved as .key.pem
"""

from Crypto.PublicKey import RSA
from Crypto import Random
import getpass
import os

random_generator = Random.new().read
key = RSA.generate(1024, random_generator)
public_key = key.publickey()
seed = 42

email = raw_input("Email: ")
password = getpass.getpass()

curr_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(curr_dir, '.login'), 'w') as f:
    f.write(public_key.encrypt(email, seed)[0])
    f.write(public_key.encrypt(password, seed)[0])

with open(os.path.join(curr_dir, '.key.pem'), 'w') as f:
    f.write(key.exportKey())
