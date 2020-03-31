#!/bin/bash
# exit when any command fails
set -e

if [ ! "$BASH_VERSION" ] ; then
    echo "Please do not use sh to run this script ($0), just execute it directly" 1>&2
    exit 1
fi

if [[ $UID != 0 ]]; then
    echo "Please run this script with sudo:"
    echo "sudo $0 $*"
    exit 1
fi

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} != 'x86_64' ]; then
    echo -e '[ERROR] 32bits (i386/i686) architectures are not supported'; exit 1;
fi

echo "Installing Host Setup Script (this may take a few minutes)..."
source /etc/os-release
case "$ID-$VERSION_ID" in

  ubuntu-16.04) apt install -y apt-transport-https software-properties-common lsb-release gnupg curl ; add-apt-repository -y ppa:deadsnakes/ppa ; apt update -y ; apt install -y python3.6 python3-pip ;;
  
  ubuntu-18.04) apt update -y ; apt install -y python3-pip curl python3.6;;
  
  centos-7) yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm ; yum install -y python3-pip curl;;
  
   *) echo -e '[ERROR] Your Operating System is not supported.\nSupported OS: CentOS 7, Ubuntu 16.04, Ubuntu 18.04'; exit 1;;
esac

rm -f /opt/xilinx/appstore/host_setup.py
mkdir -p /opt/xilinx/appstore/
curl -sL https://github.com/Accelize/xilinx-appstore/raw/master/host_setup.py > /opt/xilinx/appstore/host_setup.py
sudo chmod 777 /opt/xilinx/appstore/host_setup.py
echo "Installing Host Setup Script ... Success"
echo "> Host Setup Script Installed in /opt/xilinx/appstore/host_setup.py"
