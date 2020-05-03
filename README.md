## Piazza Automatic Related Question Recommender (PARQR)

A related question finder for Piazza courses.

This Flask API uses TF-IDF to vectorize all the posts in a Piazza course and
provides an end point to search for similar posts by providing the subject,
body, and tags of a new post.

#### Getting Started
1. Download `docker` and `docker-compose`.
2. [MAC] Download the Docker program
3. Clone this repo.
4. Inside the repo, store your Piazza credentials in an encrypted file with `python encrypt_login.py`.
5. (Step 4) Actually, ask Chirag for specific Piazza email and pw. The function read_credentials doesn't work. 
6. Spin up the docker containers with `docker-compose up --build -d`. The first time will take a few minutes to download the mongo and redis images.
7. Verify you have 5 containers running (a list of the images will be better)
8. create /data/db
9. add /data/db in Docker's Preferences' File Sharing
10. If everything went according to plan, `curl localhost` should return `Hello, World!`.
11. In Postman, enable PARQR environment. 

#### Debugging

Check out the [Debugging](https://github.com/tailorck/parqr-flask/wiki/Debugging) wiki article for more information on debugging docker problems and using Postman to test the Flask API.

#### Test

To test the application, first set the `FLASK_CONF` environment variable:

    export FLASK_CONF="testing"
    
Then run pytest in the app directory:

    pytest tests/
