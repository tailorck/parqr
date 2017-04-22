#!/bin/bash

usage="Usage: sh run.sh < development | production >"
if [ $# -ne 1 ]; then
    echo $usage
else
    if [ $1 == "development" ]; then
	gunicorn app.views:app --log-level DEBUG --timeout 300
    elif [ $1 == "production" ]; then
	gunicorn app.views:app
    fi
fi
