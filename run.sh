#!/bin/bash

usage="Usage: sh run.sh < development | production >"

if [ $# -ne 1 ]; then
    echo $usage
else
    if [ $1 == "development" ]; then
	export APP_SETTINGS="app.config.DevelopmentConfig"
	gunicorn app.views:app --log-level DEBUG --timeout 300
    elif [ $1 == "production" ]; then
	export APP_SETTINGS="app.config.ProductionConfig"
	gunicorn app.views:app
    fi
fi
