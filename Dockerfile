FROM python:3.6
ADD requirements.txt /app/requirements.txt
ADD related_courses.json /parqr/related_courses.json
RUN pip install -r /app/requirements.txt
EXPOSE 8000
ADD ./app/ /parqr/app/
RUN mkdir /parqr/logs/
RUN python -m spacy download en
WORKDIR /parqr
