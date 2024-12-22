#!/usr/bin/env bash

if [ "$1" == "setup" ]; then
    shift
    exec python setup.py "$@"
elif [ "$1" == "generate" ]; then
    shift
    exec python generate.py "$@"
else
    exec "$@"
fi
