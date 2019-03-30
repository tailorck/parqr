FROM python:2.7
ADD requirements.txt /app/requirements.txt
ADD related_courses.json /parqr/related_courses.json
RUN pip install -r /app/requirements.txt
EXPOSE 8000
ADD ./app/ /parqr/app/
RUN mkdir /parqr/logs/
ADD .key.pem /parqr/
ADD .login /parqr/
WORKDIR /parqr
