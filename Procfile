redis: redis-server
web: gunicorn --worker-class eventlet -w 1 --log-level=info --access-logfile - --error-logfile - run:app
worker: celery -A celery_worker.celery worker --loglevel=info
beat: celery -A celery_worker.celery beat --loglevel=info