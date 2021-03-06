FROM selenium/standalone-chrome

USER root

RUN apt-get update && apt-get install -y \
    python3-pip

WORKDIR /app
RUN mkdir /app/screen_caps
RUN mkdir /app/static
ADD static/ /app/static/
RUN mkdir /app/templates
ADD templates/ /app/templates/
ADD requirements.txt /app

RUN pip3 install -r requirements.txt

ADD automation.py /app
ADD tag-build.sh /app
RUN /app/tag-build.sh > /app/static/build.txt

RUN ls -R
RUN cat /app/static/build.txt

EXPOSE 5030

# Run app.py when the container launches
CMD ["python3", "automation.py"]
