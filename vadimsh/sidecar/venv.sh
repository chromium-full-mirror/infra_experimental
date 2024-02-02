#!/bin/bash

python3 -m venv pyvenv
./pyvenv/bin/python3 -m pip install --upgrade pip
./pyvenv/bin/python3 -m pip install -r requirements.txt --require-hashes
