#!/bin/bash

./pyvenv/bin/gunicorn --bind 127.0.0.1:8080 --workers 1 --threads 8 --timeout 0 main:app
