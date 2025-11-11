#!/bin/bash

IMAGE_REGISTRY=$1
IMAGE_VERSION=$2
IMAGE_NAME="rbcw-e2e-agents"

IMAGE_URL="${IMAGE_REGISTRY}/${IMAGE_NAME}"

SHORT_TAG="latest"
if [ "${DEV}" == "true" ]; then
    IMAGE_VERSION="preview-${IMAGE_VERSION}"
    SHORT_TAG="preview"
    ENVIRONMENT="${ENVIRONMENT}-preview"
fi

docker build \
    -t ${IMAGE_URL}:${IMAGE_VERSION} \
    -t ${IMAGE_URL}:${SHORT_TAG} \
    --build-arg REGISTRY=${IMAGE_REGISTRY} \
    . \
    -f ./docker/Dockerfile

docker push ${IMAGE_URL}:${IMAGE_VERSION}
docker push ${IMAGE_URL}:${SHORT_TAG}