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
brdcnt=$(/opt/xilinx/xrt/bin/xbutil list | grep "\[" | wc -l)
board_idx=0

if [[ $brdcnt -eq "0" ]]; then echo "No Boards Detected"; exit 3; fi
if [[ $brdcnt -gt "1" ]]; then read -p "> Please select the index of board you want to use:  " board_idx; fi

## FPGA Device Identification
MGMTDEV=$(/opt/xilinx/xrt/bin/xbutil scan | grep "\[$board_idx\]mgmt" | cut -d']' -f3 | cut -d: -f6)
XOCLDEV=$(/opt/xilinx/xrt/bin/xbutil scan | grep "\[$board_idx\]user" | cut -d']' -f3 | cut -d: -f6)
XILINX_FPGA_DEV_IDS="--device=/dev/dri/renderD${XOCLDEV}:/dev/dri/renderD${XOCLDEV} --device=/dev/xclmgmt${MGMTDEV}:/dev/xclmgmt${MGMTDEV} "
echo "> Found following FPGA Devices: $XILINX_FPGA_DEV_IDS"
echo "> Set XILINX_FPGA_DEV_IDS environment variable"
unset board_idx
unset MGMTDEV
unset XOCLDEV
