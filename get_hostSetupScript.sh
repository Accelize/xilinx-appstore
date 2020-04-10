#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "Please do not use sh to run this script ($0), just execute it directly" 1>&2
    exit 1
fi

if [[ $UID == 0 ]]; then
    echo "Please, do not run this script with sudo"
    exit 1
fi

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} != 'x86_64' ]; then
    echo -e '[ERROR] 32bits (i386/i686) architectures are not supported'; exit 1;
fi

echo "Installing Host Setup Script (this may take a few minutes)..."
source /etc/os-release
case "$ID-$VERSION_ID" in

  ubuntu-16.04) sudo apt update -y ; sudo apt install -y python-pip linux-headers-`uname -r` sudo || exit 1;;
  
  ubuntu-18.04) sudo apt update -y ; sudo apt install -y python-pip linux-headers-`uname -r` sudo || exit 1;;
  
  centos-7) sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm; sudo yum install -y python-pip kernel-headers kernel-devel sudo || exit 1;;
  
   *) echo -e '[ERROR] Your Operating System is not supported.\nSupported OS: CentOS 7, Ubuntu 16.04, Ubuntu 18.04'; exit 1;;
esac

python2.7 -m pip --disable-pip-version-check install --user ruamel.yaml || exit 1
sudo rm -f /opt/xilinx/appstore/host_setup.py
sudo mkdir -p /opt/xilinx/appstore/ && sudo chmod -R 777 /opt/xilinx/appstore
curl -L https://github.com/Accelize/xilinx-appstore/raw/master/host_setup.py > /opt/xilinx/appstore/host_setup.py || exit 1
sudo chmod 777 /opt/xilinx/appstore/host_setup.py
echo "Installing Host Setup Script ... Success"
echo "> Host Setup Script Installed in /opt/xilinx/appstore/host_setup.py"
