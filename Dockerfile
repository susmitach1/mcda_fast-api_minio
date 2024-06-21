# FROM naxa/python:3.9-slim

# RUN mkdir app
# WORKDIR /app

# RUN apt-get -y update
# RUN apt-get -y --no-install-recommends install \
# curl \
# libpangocairo-1.0-0 \
# libpq-dev \
# python-dev \
# libproj-dev \
# libc-dev \
# binutils \
# gettext \
# make \
# cmake \
# gcc \
# gdal-bin \
# libgdal-dev \
# g++ 

# ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
# ENV C_INCLUDE_PATH=/usr/include/gdal

# ENV PATH="${PATH}:/root/.local/bin"
# ENV PYTHONPATH=.

# COPY requirements.txt .

# RUN pip install --upgrade pip
# RUN pip install --no-cache-dir setuptools==57.5.0
# RUN pip install -r requirements.txt

# COPY migrations .
# COPY pyproject.toml .

# COPY src/ .
FROM naxa/python:3.9-slim

RUN mkdir app
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

COPY requirements.txt .
COPY apt_requirements.txt .
RUN pip install --upgrade pip
RUN apt-get update && \
    xargs -a apt_requirements.txt && \
    apt-get install -y && \
    apt-get clean
    
RUN pip install -r requirements.txt


COPY migrations .
COPY pyproject.toml .

COPY src/ .