# Makefile for the dmemo project

.PHONY: run-dev run-prod format clean

run-dev:
	FLASK_APP=dmemo.app FLASK_ENV=development flask run --host=0.0.0.0

run-prod:
	gunicorn --workers 4 --bind 0.0.0.0:5000 "dmemo.app:create_app()"

clean:
	rm -rf __pycache__ .pytest_cache dist build *.egg-info