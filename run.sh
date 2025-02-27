#!/bin/bash

# specify the txt file containing the requirements
requirements="./25PythonBitTorrent/requirements.txt"

# check if the file exists
if [ -f "$requirements" ]; then
  # read the file and install the requirements
  pip3 install $(cat "$requirements")
  
  # check if pip install was successful
  if [ $? -eq 0 ]; then
    echo "Requirements installed successfully."
    python3 ./25PythonBitTorrent/main.py
  else
    echo "Error: Failed to install requirements."
  fi
else
  echo "Error: $requirements not found!"
fi
