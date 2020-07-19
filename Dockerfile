FROM selenium/standalone-chrome

USER root

RUN apt-get update && apt-get install -y \
    python3-pip

ADD requirements.txt /
RUN pip3 install -r requirements.txt

ADD annotate.appen.py /
RUN date > /build.txt
