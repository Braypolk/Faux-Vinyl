from waitress import serve
from app import create_app

if __name__ == '__main__':
    app = create_app()
    serve(app, host='0.0.0.0', port=8787, threads=6,
          max_request_body_size=app.config['MAX_CONTENT_LENGTH'], channel_timeout=120, expose_tracebacks=False)
