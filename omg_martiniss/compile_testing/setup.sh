#!/bin/bash

sudo apt-get install git
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git $HOME/depot_tools
export PATH="$PATH:$HOME/depot_tools"

mkdir ~/chromium && cd ~/chromium
time fetch --nohooks --no-history chromium
sudo apt-get install gcc-arm-linux-gnueabihf g++-6-arm-linux-gnueabihf
