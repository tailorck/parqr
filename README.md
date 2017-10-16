### Piazza Automatic Related Question Recommender (PARQR)

A related question finder for Piazza courses.

This Flask API uses TF-IDF to vectorize all the posts in a Piazza course and
provides an end point to search for similar posts by providing the subject,
body, and tags of a new post.

### Run

To run the API, use the run script:

    bash run.sh < -d | -p | -t >
