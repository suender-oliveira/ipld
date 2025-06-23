#!/usr/bin/env bash

echo "Calling /health/ping on the ${APP_ENV} environment"
curl "http://${APP_HOSTNAME}:${APP_PORT}/health/ping"
