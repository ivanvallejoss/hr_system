release: python3 manage.py migrate && python3 manage.py collectstatic --noinput
web: python manage.py migrate && gunicorn config.wsgi --log-file -