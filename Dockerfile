FROM selenium/standalone-firefox

USER root

RUN apt-get update && apt-get install -y python3-pip

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Install production dependencies.
ENV APP_HOME /app
WORKDIR $APP_HOME
ADD ../requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
# RUN apt-get install -y chromium-browser
RUN apt-get install -y nano
COPY . ./
RUN date > /app/static/build.txt

USER seluser

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 automation:app
