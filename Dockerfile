FROM python:3.6.5-alpine3.7

RUN pip install pipenv
WORKDIR /root
# This should not be running as root, but nvm now
ADD Pipfile.lock /root/Pipfile.lock
RUN pipenv install --ignore-pipfile

ENTRYPOINT ["/usr/local/bin/pipenv", "run", "python", "/root/app/sync.py"]
