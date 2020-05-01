import boto3


def lambda_handler(event, context):
    print(event, context)

    course_id = event.get("course_id")
    user_id = event.get("user_id")

    db = boto3.client("dynamodb")
    db.update_item(
        TableName="Courses",
        Key={
            'course_id': {
                "S": course_id
            }
        },
        UpdateExpression="ADD parqr_users :i, SET num_parqr_users = ",
        ExpressionAttributeValues={
            ':i': {
                "SS": [user_id],
            }
        },
    )

    print("Added user {} to course {}".format(user_id, course_id))
