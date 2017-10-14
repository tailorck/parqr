#!/bin/bash

usage="Usage: sh run.sh < -d | -p | -t >"

while getopts ":dpt" opt; do
    case $opt in
        d)
            OPTION="d"
            export FLASK_CONF="development"
            gunicorn app.api:app --reload --log-level DEBUG --timeout 300
            ;;
        p)
            OPTION="p"
            export FLASK_CONF="production"
            gunicorn app.api:app
            ;;
        t)
            OPTION="t"
            export FLASK_CONF="testing"
            gunicorn app.api:app --reload --log-level DEBUG --timeout 300
            ;;
        \?)
            echo $usage
            ;;
    esac
done

if [ -z $OPTION ]; then
    echo $usage
fi
