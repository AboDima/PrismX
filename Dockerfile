FROM python:3.7
COPY . /
WORKDIR /
RUN apt-get update -y && apt-get install redis  libpython-dev -y
RUN pip3 install -r requirements.txt 
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
CMD celery -A app worker -l info && celery -A app beat -l info && python3 manage.py runserver 0.0.0.0:8000