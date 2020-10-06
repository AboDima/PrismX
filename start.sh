redis-server &
celery -A app worker -l info &
celery -A app beat -l info &
python3 manage.py makemigrations &
python3 manage.py migrate &
python3 manage.py runserver 0.0.0.0:8000