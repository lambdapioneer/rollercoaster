#!/bin/bash
docker run --mount type=bind,source="$(pwd)/pickles",target=/rollercoaster/pickles -it rollercoaster "/rollercoaster/scripts/coverage.sh";
docker run --mount type=bind,source="$(pwd)/pickles",target=/rollercoaster/pickles -it rollercoaster-pypy "/rollercoaster/scripts/coverage.sh";