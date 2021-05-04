FROM python:3.7

WORKDIR /rollercoaster

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY input /rollercoaster/input
COPY scripts /rollercoaster/scripts
COPY simulation /rollercoaster/simulation
COPY tests /rollercoaster/tests
COPY *.py /rollercoaster/
COPY *.ipynb /rollercoaster/
