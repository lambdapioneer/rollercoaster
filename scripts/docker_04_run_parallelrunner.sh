#!/bin/bash
docker run --mount type=bind,source="$(pwd)/pickles",target=/rollercoaster/pickles -it rollercoaster sh -c "python3 parallelrunner.py pickles/*input";