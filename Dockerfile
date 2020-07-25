FROM selenium/standalone-chrome

USER root

RUN apt-get update && apt-get install -y \
    python3-pip

WORKDIR /app
RUN mkdir /app/static
ADD static/ /app/static/
ADD requirements.txt /app

RUN pip3 install -r requirements.txt

ADD annotate.appen.py /app
RUN date > /app/static/build.txt

RUN ls -R
RUN cat /app/static/build.txt

EXPOSE 5030

# Run app.py when the container launches
CMD ["python3", "annotate.appen.py"]
