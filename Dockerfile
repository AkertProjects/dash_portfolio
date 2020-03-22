FROM python:3.7.2-stretch as python
ENV PYTHONPATH="/analytics/python/:${PYTHONPATH}"
LABEL maintainer="Erik Akert <akerterik@gmail.com>"
RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip
RUN apt-get install libapache2-mod-wsgi-py3 -y
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
COPY ./ /app
WORKDIR /app
