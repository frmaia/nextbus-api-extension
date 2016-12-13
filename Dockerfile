FROM python:2.7
MAINTAINER Felipe Maia "frmaia.br@gmail.com"

RUN apt-get update -y 

ADD . /nextbust-extension-api
WORKDIR /nextbust-extension-api
RUN pip install -r requirements.txt
