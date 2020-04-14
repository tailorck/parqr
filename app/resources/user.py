from flask_restful import Resource


class Users(Resource):

    def post(self):
        return {"message": "user service currently disable"}, 500

        # TODO: Fix this
        # username = request.json.get('username')
        # password = request.json.get('password')

        # if User.objects(username=username).first() is not None:
        #     return {'message': 'Username already enrolled'}, 400

        # user = User(username=username)
        # user.hash_password(password)
        # user.save()
        # return {'username': user.username}, 201
