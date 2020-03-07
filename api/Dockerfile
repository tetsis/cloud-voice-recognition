FROM python:3.8
RUN mkdir -p /usr/src/api/src
ADD requirements.txt /usr/src/api/
ADD src /usr/src/api/src/
WORKDIR /usr/src/api
RUN pip install -r requirements.txt