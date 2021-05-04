#!/bin/bash
docker build -t rollercoaster -f Dockerfile .;
docker build -t rollercoaster-pypy -f Dockerfile-pypy .;