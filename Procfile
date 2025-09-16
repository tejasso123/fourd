web: uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000}
worker: celery -A app.celery_app.mk_celery worker --loglevel=info --pool=solo