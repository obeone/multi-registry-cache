#!/usr/bin/env bash

# Entrypoint script for Docker container
# This script checks the first argument and executes the corresponding Python script or command.
# Usage:
#   ./entrypoint.sh setup [args]    - Runs python setup.py with the given arguments
#   ./entrypoint.sh generate [args] - Runs python generate.py with the given arguments
#   ./entrypoint.sh [command]       - Executes the given command

# Check if the first argument is empty
if [ -z "$1" ]; then
    echo "No command provided. Exiting."
    exit 1
fi

if [ "$1" == "setup" ]; then
    shift
    # Execute setup.py with remaining arguments
    exec python setup.py "$@"
elif [ "$1" == "generate" ]; then
    shift
    # Execute generate.py with remaining arguments
    exec python generate.py "$@"
else
    # Execute the provided command as is
    exec "$@"
fi
