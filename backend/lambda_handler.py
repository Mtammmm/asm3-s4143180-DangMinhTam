import serverless_wsgi

from app import create_app


application = create_app()


def handler(event, context):
    return serverless_wsgi.handle_request(application, event, context)
