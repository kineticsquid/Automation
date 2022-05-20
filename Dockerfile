FROM selenium/standalone-firefox

USER root

RUN apt-get update && apt-get install -y python3-pip

# Set the working directory to /app
WORKDIR /app

# copy the requirements file used for dependencies
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY . .

RUN apt-get install -y nano
RUN date > /app/static/build.txt

USER seluser

RUN ls -R

RUN python3 --version

ENTRYPOINT ["python3", "app.py"]
