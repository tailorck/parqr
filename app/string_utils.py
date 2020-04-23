import spacy
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
        return_list.append(followup['text'])
        return_list += followup['responses']

    return ' '.join(return_list)


def lambda_handler(event, context):
    print(event, context)

    if event["source"] == "ModelTrain":
        print("ModelTrain source")
        posts = event["posts"]
        print("{} posts".format(len(posts)))

        model_name = event["model_name"]
        words = []
        model_pid_list = []

        for post in posts:
            if model_name == "POST":
                clean_subject = spacy_clean(post.get("subject"))
                clean_body = spacy_clean(post.get("body"))
                tags = post.get("tags")
                words.append(' '.join(clean_subject + clean_body + tags))
                model_pid_list.append(post["post_id"])
            elif model_name == "I_ANSWER":
                if post.get("i_answer"):
                    words.append(' '.join(spacy_clean(post["i_answer"])))
                    model_pid_list.append(post["post_id"])
            elif model_name == "S_ANSWER":
                if post.get("s_answer"):
                    words.append(' '.join(spacy_clean(post["s_answer"])))
                    model_pid_list.append(post["post_id"])
            elif model_name == "FOLLOWUP":
                if post.get("followups") and len(post["followups"]) < 15:
                    followup_str = stringify_followups(post["followups"])
                    words.append(' '.join(spacy_clean(followup_str)))
                    model_pid_list.append(post["post_id"])

        response = {
            "words": words,
            "model_pid_list": model_pid_list
        }
        print(response)
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
