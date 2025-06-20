FROM apache/airflow:2.10.2-python3.10

USER root

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

#COPY ../requirements.txt requirements.txt
#
#RUN pip3 install -qr requirements.txt
