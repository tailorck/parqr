import logging
import spacy

logger = logging.getLogger('app')


def spacy_clean(text, array=True):
    '''
    Cleans a string of text by:
        1. Removing all punctuations
        2. Stemming all words
        3. Decapitalize non-proper nouns
        4. Removing all pronouns

        After installation you need to download a language model.
        python -m spacy download en

        Verify all installed models are compatible with spaCy version
        python -m spacy validate
        :param text: input string
        :return: array of cleaned tokens
    '''
    #loading model
    nlp = spacy.load("en_core_web_sm")
    #creating a doc object by applying model to the text
    doc = nlp(text)
    res = [token.lemma_ for token in doc if token.pos_ not in {"PUNCT", "PART", "PRON"}]
    return res if array else "".join(res)


def stringify_followups(followup_list):
    return_list = []
    for followup in followup_list:
        return_list.append(followup['text'])
        return_list += followup['responses']

    return ' '.join(return_list)
