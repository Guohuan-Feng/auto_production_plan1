#/bin/bash

gunicorn -w ${WORK_COUNT} \
    -b 0.0.0.0:${SERVICE_PORT} \
    -k uvicorn.workers.UvicornWorker app.api:app \
    -t 600