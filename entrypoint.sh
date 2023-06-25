#!/bin/sh

python manage.py migrate --no-input
python manage.py collectstatic --no-input

gunicorn star_burger.wsgi:application -b 0.0.0.0:8179 
