FROM python:3.7
COPY . /
WORKDIR /
RUN apt-get update -y && apt-get install redis  libpython-dev -y
RUN pip install -r requirements.txt 
RUN python manage.py makemigrations
RUN python manage.py migrate
CMD celery -A app worker -l info && celery -A app beat -l info && python manage.py runserver 0.0.0.0:8000