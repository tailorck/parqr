from app import app
from app.parqr import get_all_posts_as_words
from flask import jsonify, make_response, request

post = {
    'folders': 'h2q4',
    'history': [{
        'anon': u'stud',
        'content': u'<p>I am trying to read the zip code values</p>',
        u'created': u'2017-03-02T20:10:11Z',
        u'subject': u'CSV reading zipcode',
        u'uid':
        u'hz1jr5fxbj16y'}]
}


@app.route('/')
def index():
    return "Hello, World!"


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 400)


@app.route('/api/v1.0/similar_posts', methods=['GET'])
def similar_posts():
    # localhost:5000/api/v1.0/similar_posts&keywords=hey&keywords=hi
    post['keywords'] = request.args.getlist('keywords')
    return jsonify(post)


def all_posts():
    return jsonify(get_all_posts_as_words())


if __name__ == "__main__":
    app.run(debug=True)
