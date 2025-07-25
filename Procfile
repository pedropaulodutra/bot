web: gunicorn config.wsgi --log-file -
worker: celery -A config worker -l info -P gevent
release: python manage.py collectstatic --no-input && python manage.py migrate