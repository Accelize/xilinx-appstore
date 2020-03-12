#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "Please do not use sh to run this script ($0), just execute it directly" 1>&2
    exit 1
fi

if [[ $UID != 0 ]]; then
    echo "Please run this script with sudo:"
    echo "sudo $0 $*"
    exit 1
fi

echo "Installing Host Setup Script ..."
source /etc/os-release
case "$ID" in
  ubuntu) sudo apt update -y > /dev/null 2>&1 && sudo apt -qq install -y python3-pip curl > /dev/null 2>&1 ;;
  centos) sudo yum install -y epel-release > /dev/null 2>&1 && sudo yum install -y python3-pip curl > /dev/null 2>&1;;
       *) echo -e '[ERROR] Your Operating System is not supported.\nSupported OS: CentOS, Ubuntu' ;; 
esac

rm -f /opt/xilinx/appstore/host_setup.py
mkdir -p /opt/xilinx/appstore/
curl -sL https://github.com/Accelize/xilinx-appstore/raw/master/host_setup.py > /opt/xilinx/appstore/host_setup.py
echo "Installing Host Setup Script ... Success"
echo "> Host Setup Script Installed in /opt/xilinx/appstore/host_setup.py"
