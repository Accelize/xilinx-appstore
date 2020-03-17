
# Xilinx AppStore - Host Setup Script

## Install the Host Setup Script
````bash
curl -sL https://tinyurl.com/getHostSetup | sudo bash
````

## Run the Host Setup Script
Run the host setup script with **vendor_name** and **app_name** arguments
````bash
python3 /opt/xilinx/appstore/host_setup.py -v {vendor_name} -a {app_name}
````

*e.g: python3 /opt/xilinx/appstore/host_setup.py -v ngcodec -a hevc_enc_dual*

**Note:** Run the host setup script without arguments to get the list of available applications

**Note:** The setup script might require to reboot the host. In this case, please reboot the host and launch the script again until setup is complete.

## Add your application
- Add section in file 'xilinx_appstore_appdefs/applist.yaml'
- Add YAML description file in 'xilinx_appstore_appdefs/apps'
- Check YAML syntax with command : 
````bash
yamllint -c .yamllint xilinx_appstore_appdefs/apps
````


