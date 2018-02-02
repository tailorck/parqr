import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname))


setup(
    name="PARQR",
    version="0.0.1",
    author="Chirag Tailor",
    author_email="cktailor34@gmail.com",
    description="Piazza Automated Related Question Recommender",
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Flask",
    ],
    packages=find_packages(exclude=['tests', 'logs', 'chrome-extension'])
)
