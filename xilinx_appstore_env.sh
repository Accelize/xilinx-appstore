#!/bin/bash

# Make sure this script is sourced
script=${BASH_SOURCE[0]}
if [ $script == $0 ]; then
    echo "ERROR: You must source this script"
    exit 2
fi

# Board selection
/opt/xilinx/xrt/bin/xbutil list
read -p "> Please select the index of board you want to use:  " board_idx

## FPGA Device Identification
MGMTDEV=$(/opt/xilinx/xrt/bin/xbutil scan | grep "\[$board_idx\]mgmt" | cut -d']' -f3 | cut -d: -f6)
XOCLDEV=$(/opt/xilinx/xrt/bin/xbutil scan | grep "\[$board_idx\]user" | cut -d']' -f3 | cut -d: -f6)
XILINX_FPGA_DEV_IDS="--device=/dev/dri/renderD${XOCLDEV}:/dev/dri/renderD${XOCLDEV} --device=/dev/xclmgmt${MGMTDEV}:/dev/xclmgmt${MGMTDEV} "
echo "> Found following FPGA Devices: $XILINX_FPGA_DEV_IDS"
echo "> Set XILINX_FPGA_DEV_IDS environment variable"
unset board_idx
unset MGMTDEV
unset XOCLDEV
