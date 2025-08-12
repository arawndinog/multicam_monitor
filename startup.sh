#!/bin/bash

source $HOME/miniconda3/bin/activate
conda activate cam_streaming
cd $HOME/Projects/multicam_monitor
python -u cam.py

