release: python3 manage.py migrate && python3 manage.py collectstatic --noinput
web: gunicorn config.wsgi --log-file -