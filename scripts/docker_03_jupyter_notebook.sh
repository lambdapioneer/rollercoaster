#!/bin/bash
docker run --mount type=bind,source="$(pwd)/pickles",target=/rollercoaster/pickles -p 8888:8888 -it rollercoaster sh -c "jupyter notebook --ip=0.0.0.0 --allow-root";