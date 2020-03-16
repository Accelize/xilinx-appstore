#!/bin/bash
export LANG=en_US.UTF-8 && export LANGUAGE=en_US.UTF-8 && export LC_COLLATE=C && export LC_CTYPE=en_US.UTF-8

if [ ! "$BASH_VERSION" ] ; then
    echo "Please do not use sh to run this script ($0), just execute it directly" 1>&2
    exit 1
fi

# Make sure this script is sourced
script=${BASH_SOURCE[0]}
if [ $script == $0 ]; then
    echo "ERROR: You must source this script"
    exit 2
fi

# Board selection
sudo /opt/xilinx/xrt/bin/awssak list
brdcnt=$(sudo /opt/xilinx/xrt/bin/awssak list | grep "\[" | wc -l)
board_idx=0

if [[ $brdcnt -eq "0" ]]; then echo "No Boards Detected"; exit 3; fi
if [[ $brdcnt -gt "1" ]]; then read -p "> Please select the index of board you want to use:  " board_idx; fi

## FPGA Device Identification
XOCLDEV=$(sudo /opt/xilinx/xrt/bin/awssak scan | grep "\[$board_idx\]user" | cut -d':' -f6 | cut -d']' -f1)
XILINX_FPGA_DEV_IDS="--device=/dev/dri/renderD${XOCLDEV}:/dev/dri/renderD${XOCLDEV}"
XILINX_FPGA_DEV_IDS+=" --mount type=bind,source=/sys/bus/pci/devices/0000:00:1d.0,target=/sys/bus/pci/devices/0000:00:1d.0"
XILINX_FPGA_DEV_IDS+=" --mount type=bind,source=/sys/bus/pci/devices/0000:00:1e.0,target=/sys/bus/pci/devices/0000:00:1e.0"

echo "> Found following FPGA Devices: $XILINX_FPGA_DEV_IDS"
echo "> Set XILINX_FPGA_DEV_IDS environment variable"
unset board_idx
unset XOCLDEV
