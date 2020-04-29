import boto3


def lambda_handler(event, context):
    client = boto3.client("lambda")
    print(event, context)

    function_names = [
        "Parqr-ModelTrain",
        "Parser",
        "Parqr-API",
        "Parqr",
        "Feedbacks",
        "Parqr-Cleaner",
        "Dashboard"
    ]

    for function in function_names:
        s3_key = event.get("Records")[0].get("s3").get("object").get("key")
        if "master" in s3_key:
            if function == "Parqr-API":
                client.update_function_configuration(
                    FunctionName=function,
                    Environment={
                        'Variables': {
                            'stage': 'prod'
                        }
                    }
                )

            response = client.update_function_code(
                FunctionName=function,
                S3Bucket="git-to-amazon-s3-outputbucket-7xiedlur8bgn",
                S3Key=s3_key,
                Publish=True
            )
            version = response.get("Version")
            print("Created new version {} for lambda {}".format(version, function))

            if function == "Parqr-API":
                client.update_function_configuration(
                    FunctionName=function,
                    Environment={
                        'Variables': {
                            'stage': 'dev'
                        }
                    }
                )

            aliases = client.list_aliases(
                FunctionName=function
            ).get("Aliases")

            for alias in aliases:
                if alias.get("Name") == "PROD":
                    client.update_alias(
                        FunctionName=function,
                        Name='PROD',
                        FunctionVersion=version
                    )
                    print("Updated alias PROD for function {} with new version {}"
                          .format(function, version))
        else:
            client.update_function_code(
                FunctionName=function,
                S3Bucket="git-to-amazon-s3-outputbucket-7xiedlur8bgn",
                S3Key=s3_key
            )
