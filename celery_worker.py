from app import create_app, init_celery

app = create_app()
celery = init_celery(app)
