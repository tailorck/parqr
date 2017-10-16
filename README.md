### Piazza Automatic Related Question Recommender (PARQR)

A related question finder for Piazza courses.

This Flask API uses TF-IDF to vectorize all the posts in a Piazza course and
provides an end point to search for similar posts by providing the subject,
body, and tags of a new post.

### Run

To run the API, use the run script:

    bash run.sh < -d | -p | -t >

### Test

To test the application, first set the `FLAKS_CONF` environment variable:

    export FLASK_CONF="testing"
    
Then run pytest in the app directory:

    pytest app/
