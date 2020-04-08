# FROM python:3.6-alpine
# 
# ADD requirements.txt /app/requirements.txt
# 
# RUN apk add --update --no-cache --virtual .build-deps make automake gcc g++ subversion python3-dev musl-dev \
#  && pip install cython \
#  && pip install -r /app/requirements.txt \
#  && apk del .build-deps
FROM python:3.6

ADD requirements.txt /parqr/requirements.txt
RUN pip install -r /parqr/requirements.txt
RUN python -m spacy download en_core_web_sm

ADD ./app/ /parqr/app/
ADD ~/.aws/config ~/.aws/config
ADD ~/.aws/credentials ~/.aws/credentials
RUN mkdir /parqr/logs/
EXPOSE 8000
WORKDIR /parqr
