release: python manage.py migrate && python manage.py collectstatic --noinput && python manage.py createsuperuser --noinput || true
web: gunicorn config.wsgi --log-file -