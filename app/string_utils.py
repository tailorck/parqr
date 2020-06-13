import boto3
import spacy
from botocore.exceptions import ClientError

from enum import Enum


class TFIDF_MODELS(Enum):
    POST = 0
    I_ANSWER = 1
    S_ANSWER = 2
    FOLLOWUP = 3


# loading model
nlp = spacy.load("en_core_web_sm")


def spacy_clean(text, array=True):
    '''
    Cleans a string of text by:
        1. Removing all punctuations
        2. lemmatization on all words
        3. Decapitalize non-proper nouns
        4. Removing all pronouns

        After installation you need to download a language model.
        python -m spacy download en

        Verify all installed models are compatible with spaCy version
        python -m spacy validate
        :param text: input string
        :return: array of cleaned tokens
    '''

    # creating a doc object by applying model to the text
    if text is not None:
        doc = nlp(text)
        res = [token.lemma_ for token in doc if token.pos_ not in {"PUNCT", "PART", "PRON"}]
        return res if array else " ".join(res)
    else:
        return [] if array else ""


def stringify_followups(followup_list):
    return_list = []
    # print("{} followups".format(len(followup_list)))
    for followup in followup_list:
        if followup.get('text'):
            return_list.append(followup['text'])
        if followup.get('responses'):
            return_list += followup['responses']

    return ' '.join(return_list)


def lambda_handler(event, context):
    if event["source"] == "ModelTrain":
        print("ModelTrain source")
        posts = event["posts"]
        course_id = event["course_id"]
        print("{} posts for course {}".format(len(posts), course_id))

        dynamodb = boto3.resource('dynamodb')
        course_table = dynamodb.Table(course_id)

        model_name = event["model_name"]
        words = []
        model_pid_list = []

        for post in posts:
            if model_name == "POST":
                if not post.get("POST_words"):
                    clean_subject = spacy_clean(post.get("subject"))
                    clean_body = spacy_clean(post.get("body"))
                    tags = post.get("tags")
                    words.append(' '.join(clean_subject + clean_body + tags))
                    try:
                        course_table.update_item(
                            Key={
                                "post_id": post["post_id"]
                            },
                            UpdateExpression='SET POST_words = :post_words',
                            ExpressionAttributeValues={
                                ':post_words': ' '.join(clean_subject + clean_body + tags),
                            }
                        )
                    except ClientError:
                        pass
                else:
                    words.append(post.get("POST_words"))
                model_pid_list.append(post["post_id"])
            elif model_name == "I_ANSWER":
                if post.get("i_answer"):
                    if not post.get("I_ANSWER_words"):
                        i_answer = ' '.join(spacy_clean(post["i_answer"]))
                        words.append(i_answer)
                        if len(i_answer) > 0:
                            try:
                                course_table.update_item(
                                    Key={
                                        "post_id": post["post_id"]
                                    },
                                    UpdateExpression='SET I_ANSWER_words = :words',
                                    ExpressionAttributeValues={
                                        ':words': i_answer,
                                    }
                                )
                            except ClientError:
                                pass
                    else:
                        words.append(post.get("I_ANSWER_words"))
                    model_pid_list.append(post["post_id"])
            elif model_name == "S_ANSWER":
                if post.get("s_answer"):
                    if not post.get("S_ANSWER_words"):
                        s_answer = ' '.join(spacy_clean(post["s_answer"]))
                        words.append(s_answer)

                        if len(s_answer) > 0:
                            try:
                                course_table.update_item(
                                    Key={
                                        "post_id": post["post_id"]
                                    },
                                    UpdateExpression='SET S_ANSWER_words = :words',
                                    ExpressionAttributeValues={
                                        ':words': s_answer,
                                    }
                                )
                            except ClientError:
                                pass
                    else:
                        words.append(post.get("S_ANSWER_words"))
                    model_pid_list.append(post["post_id"])
            elif model_name == "FOLLOWUP":
                if post.get("followups") and len(post["followups"]) < 15:
                    if not post.get("FOLLOWUP_words"):
                        followup_str = stringify_followups(post["followups"])
                        followup_words = ' '.join(spacy_clean(followup_str))
                        words.append(followup_words)
                        if len(followup_words) > 0:
                            try:
                                course_table.update_item(
                                    Key={
                                        "post_id": post["post_id"]
                                    },
                                    UpdateExpression='SET FOLLOWUP_words = :words',
                                    ExpressionAttributeValues={
                                        ':words': followup_words,
                                    }
                                )
                            except ClientError:
                                pass
                    else:
                        words.append(post.get("FOLLOWUP_words"))
                    model_pid_list.append(post["post_id"])

        response = {
            "words": words,
            "model_pid_list": model_pid_list
        }
        print("{} words for {} posts".format(len(response["words"]), len(response["model_pid_list"])))
        return response
    elif event["source"] == "Query":
        print("Query source")
        query = event["query"]
        clean_query = spacy_clean(query, array=False)
        response = {
            "clean_query": clean_query
        }
        print(response)
        return response
