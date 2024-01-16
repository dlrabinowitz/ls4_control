FROM python:3.11-slim-bullseye

LABEL maintainer="gallegoj@uw.edu"

WORKDIR /opt

COPY . archon

RUN apt-get -y update
RUN apt-get -y install build-essential libbz2-dev

RUN pip3 install -U pip setuptools wheel
RUN cd archon && pip3 install .

# Connect repo to package
LABEL org.opencontainers.image.source https://github.com/sdss/archon

ENTRYPOINT archon actor start --debug
