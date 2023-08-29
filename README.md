# PredictiveDCI

This repository contains the code used to run the simulations for the paper "A hierarchical architecture for predictive monitoring of distributed critical infrastructures". The scenario simulated is a hierachical system of processing units with three levels. For more information, please refer to the paper.

The simmulation generates a svg file with the results of the simulation. Parameters of the simulation can be changed in the `./sim/config.yaml` file.

# Setup

1. `python -m venv .venv`

2. `source .venv/bin/activate`

3. `pip install -r ./requirements.txt`

## Run

Run the simulation with `python ./sim/scenario.py` or `python3 ./sim/scenario.py` depending on your system. If you are using a virtual environment, you can also run it with `.venv/Scripts/python.exe ./sim/scenario.py` or `.venv/bin/python ./sim/scenario.py` depending on your system.