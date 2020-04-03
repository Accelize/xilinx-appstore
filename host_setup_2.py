#!/usr/bin/env python2
# coding=utf-8
"""
"""
import os, sys, shutil, json, argparse, getpass
from subprocess import Popen, PIPE
from io import open

REQ_PYTHON = (2, 7)
REQUIRED_PYTHON_MODULES = ['ruamel.yaml']
SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))
SCRIPT_VERSION='v0.1.1'
REPO_DIR='/tmp/xilinx-appstore'
REPO_TARBALL_URL='https://api.github.com/repos/Accelize/xilinx-appstore/tarball'
APPDEFS_FOLDER=os.path.join(REPO_DIR, "xilinx_appstore_appdefs")
APPLIST_FNAME="applist.yaml"
SETENV_SCRIPT=os.path.join(REPO_DIR, 'xilinx_appstore_env.sh')
SETENV_SCRIPT_AWS=os.path.join(REPO_DIR, 'xilinx_appstore_aws_env.sh')
XRT_BIN='xbutil'
AWS_BIN='awssak'

def parse_value(key_value):
    return key_value.split('=')[1].rstrip().strip('""').lower()
   

def download_appstore_catalog():
    if os.path.exists(REPO_DIR):
        shutil.rmtree(REPO_DIR, ignore_errors=True)
    os.makedirs(REPO_DIR)
    cmd ='sudo curl -sL %s | tar xzf - -C %s --strip 1' % (REPO_TARBALL_URL, REPO_DIR)
    exec_cmd_with_ret_output(cmd)


def print_status(text, status, fulllength=40):
    print(" > {0:{fill}<{size}} {1}".format(text+' ', status, fill='.', size=fulllength))
    

def jsonfile_to_dict(filename):
    with open(filename, 'r', encoding="utf-8") as json_file:
        return json.load(json_file)


def yamlfile_to_dict(filename):
    from ruamel.yaml import YAML
    yaml=YAML(typ='safe')
    with open(filename, 'r', encoding="utf-8") as yaml_file:
        return yaml.load(yaml_file)
        

def dict_to_yamlfile(d, filename):
    from ruamel.yaml import YAML
    yaml=YAML()
    with open(filename, 'w', encoding="utf-8") as yaml_file:
        yaml.dump(d, yaml_file)
        
        
def dict_pretty_print(in_dict):
    print(json.dumps(in_dict, sort_keys=True, indent=4))
    
    
def ask_user_update_permission():
    answer = None
    while answer not in ['y', 'n']:
        answer = raw_input(" > Start install/update process (y/n)? ").lower()
        if answer == 'y':
            break
        if answer == 'y':
            sys.exit(1)
    

def exec_cmd_with_ret_output(cmd, path='.'): 
    try:
        cmd = 'cd %s && %s' %(path, cmd)
        p = Popen(cmd, shell=True, stdout=PIPE)
        stdout, stderr = p.communicate()        
        out = '' if stdout is None else stdout.decode('utf8')
        err = '' if stderr is None else stderr.decode('utf8')
        return p.returncode, out, err
    except KeyboardInterrupt as e:
        raise(e)


def fpga_board_list():
    fpga_boards=[]
    ret, out, err = exec_cmd_with_ret_output('sudo lspci  -d 10ee: | grep " Processing accelerators" | grep "Xilinx" | cut -d" " -f7')
    for line in out.splitlines():
        if '5000' in line: fpga_boards.append('u200') # XDMA
        if '5004' in line: fpga_boards.append('u250') # XDMA
        if '5008' in line: fpga_boards.append('u280') # ES1-XDMA
        if '500c' in line: fpga_boards.append('u280') # XDMA
        if '5010' in line: fpga_boards.append('u200') # QDMA
        if '5014' in line: fpga_boards.append('u250') # QDMA
        if '5020' in line: fpga_boards.append('u50')  # XDMA
        if '5050' in line: fpga_boards.append('u25')  # XDMA
        if '0B03' in line: fpga_boards.append('u25')  # XDMA U25 (X2)
        if 'D000' in line: fpga_boards.append('u200') # GOLDEN
    
    fpga_boards = list(dict.fromkeys(fpga_boards))
    return fpga_boards


def get_xrt_version(host_os):
    xrt=None
    if 'centos' in host_os.lower():
        ret, out, err = exec_cmd_with_ret_output("sudo yum info xrt | grep Version | cut -d ':' -f2")
        xrt=out.split('-')[0].strip()
    if 'ubuntu' in host_os.lower():
        ret, out, err = exec_cmd_with_ret_output("sudo apt-cache show xrt | grep Version | cut -d' ' -f2")
        xrt=out.strip()
    return xrt


def get_host_env():
    # Get OS
    os_release_path = (
    '/usr/lib/os-release' if os.path.exists('/usr/lib/os-release') else
    '/etc/os-release')
    host_os_version=None
    host_os=None
    with open(os_release_path, 'rt') as os_release:
        for line in os_release:
            if line.startswith('VERSION_ID='):
                host_os_version = parse_value(line)
            elif line.startswith('ID='):
                host_os = parse_value(line)
            if host_os_version and host_os:
                break
    
    if  host_os not in ['ubuntu', 'centos'] or \
        host_os == 'ubuntu' and host_os_version not in ['16.04','18.04'] or \
        host_os == 'centos' and host_os_version not in ['7'] or \
        host_os is None:
        print(" [ERROR] Your Operating System is not supported.\nSupported OS: CentOS 7, Ubuntu 16.04 and Ubuntu 18.04")
        sys.exit(1)
    return host_os, host_os_version
    
def get_fpga_env(host_os, onAWS):
    # Get FPGA Boards & Shells
    if onAWS:
        ret, out, err = exec_cmd_with_ret_output("sudo /opt/xilinx/xrt/bin/%s list | grep Found | cut -d' ' -f3" % (AWS_BIN))
    else:
        ret, out, err = exec_cmd_with_ret_output("/opt/xilinx/xrt/bin/%s list | grep Found | cut -d' ' -f4" % (XRT_BIN))
    nbBoardsFound = out.strip()
    if nbBoardsFound == '': nbBoardsFound='0'
    print_status('Board(s) Found', '%s'%nbBoardsFound)
    if nbBoardsFound == '0': 
        print(" [ERROR] No FPGA Board Detected. you need at least one FPGA board to use this application.")
        sys.exit(1)
    
    boards=[]
    shells=[]
    if onAWS:
        ret, out, err = exec_cmd_with_ret_output('sudo /opt/xilinx/xrt/bin/%s list'%(AWS_BIN))
        for num, line in enumerate(out.splitlines()):
            if line.startswith('['):
                brd_num=line.split('[')[1].split(']')[0]
                boards.append('aws_f1_%s'%brd_num)
                shells.append(line.split(' ')[1])
    else:
        ret, out, err = exec_cmd_with_ret_output('sudo /opt/xilinx/xrt/bin/%s flash scan'%(XRT_BIN))
        nlines = out.count('\n')
        for num, line in enumerate(out.splitlines()):
            if line.startswith('Card [') and (num+5) <= nlines:
                boards.append(out.splitlines()[num+2].split(':')[1].strip())
                shells.append(out.splitlines()[num+5].split(',')[0].strip())
    if not boards or not shells:
        print(" [ERROR] Unable to get boards or shells details.")
        sys.exit(1)
        
    print_status('Detected Boards', ''%boards)
    print_status('Detected Shells', ''%shells)
    return boards, shells


def dsa_format(dsa):
    char_list=['-', ' ', '.']
    for c in char_list:
        dsa=dsa.replace(c,'_')
    return dsa


def check_xrt(host_os, target_version, selected_conf):
    if check_host_pkg_installed(host_os, 'xrt'):
        xrt_version = get_xrt_version(host_os)
        if xrt_version and  xrt_version in target_version :
            print_status('XRT Version Check', 'OK (%s)' % xrt_version)
            return

    print_status('XRT Version Check', 'Update Required')
    ask_user_update_permission()
    print_status('Updating XRT', '')
    host_pkg_remove(host_os, 'xrt')
    pkg_path=host_pkg_download(selected_conf['xrt_package'])
    host_pkg_install(host_os, pkg_path)
    print_status('Updating XRT', 'Done')
    host_reboot(cold=False)

 
def check_host_dsa(host_os, selected_conf):
    conf_pkg=selected_conf['dsa_package']
    pkg_name=conf_pkg.split('-')[0]+'-'+conf_pkg.split('-')[1]+'-'+conf_pkg.split('-')[2]
    pkg_vers=conf_pkg.split('-')[3]
   
    if 'centos' in host_os: 
        ret, out, err = exec_cmd_with_ret_output('sudo yum list installed | grep %s | grep %s > /dev/null 2>&1' % (pkg_name, pkg_vers))
    else:
        ret, out, err = exec_cmd_with_ret_output('sudo apt list --installed 2>/dev/null | grep %s | grep %s > /dev/null 2>&1' % (pkg_name, pkg_vers))

    if ret:
        print_status('Board Shell [HOST] Version Check', 'Update Required (%s-%s)' % (pkg_name, pkg_vers))
        ask_user_update_permission()
        print_status('Updating Board Shell [HOST] (may take several minutes)', '')
        pkg_path=host_pkg_download(selected_conf['dsa_package'])
        host_pkg_install(host_os, pkg_path)
        print_status('Updating Board Shell [HOST]', 'Done')
        host_reboot(cold=False)
    else:
        print_status('Board Shell [HOST] Version Check', 'OK (%s-%s)' % (pkg_name, pkg_vers))


def check_kernel(host_os):
    if os.path.exists(os.path.join('/lib','modules', os.uname()[2], 'build')):
        print_status('Kernel Version Check', 'OK')
    else:
        print_status('Kernel Version Check', 'Update Required')
        ask_user_update_permission()
        print_status('Updating Kernel', '')
        update_os_kernel(host_os)     
        print_status('Updating Kernel', 'Done')
        host_reboot(cold=False)


def check_board_shell(boardIdx):
    cmd='sudo /opt/xilinx/xrt/bin/%s flash scan' % (XRT_BIN)
    ret, out, err = exec_cmd_with_ret_output(cmd)
    cnt=0
    for l in out.splitlines():
        if 'Card [%s]' % boardIdx in l:
            if(out.splitlines()[cnt+5].strip() == out.splitlines()[cnt+7].strip()):
                print_status('Board Shell Host vs. FPGA', 'OK')
                return
        cnt+=1     

    print_status('Board Shell Host vs. FPGA', 'Update Required')
    cmd=get_board_shell_flash_cmd(boardIdx)
    print(' > Update Board DSA using the following command, then do a cold reboot:')
    print(' > %s' % cmd)
    sys.exit(1)


def check_host_pkg_installed(host_os, pkg):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt list --installed 2>/dev/null | grep '+ pkg
    elif 'centos' in host_os:
        cmd = 'sudo yum list installed | grep '+ pkg
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        return False
    return True


def host_pkg_install(host_os, packages):
    print_status('Installing %s' % packages, '') 
    logfile='/tmp/xx_appstore_%s_pkg_install.log' % (os.path.basename(packages))
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get install -y '+ packages + '> ' + logfile + ' 2>&1'
    elif 'centos' in host_os:
        cmd = 'sudo yum install -y '+ packages + '> ' + logfile + ' 2>&1'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        print_status('Installing %s' % packages, 'Failed')
        print('Check log file %s for details' % logfile)
        sys.exit(1)
    print_status('Installing %s' % packages, 'OK')

 
def host_pkg_remove(host_os, packages):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get remove -y '+ packages + '> /dev/null 2>&1'
    elif 'centos' in host_os:
        cmd = 'sudo yum remove -y '+ packages + '> /dev/null 2>&1'
    exec_cmd_with_ret_output(cmd)

def host_pkg_download(pkg):
    print_status('Downloading %s' % pkg, '')
    cmd = 'curl -sL https://www.xilinx.com/bin/public/openDownload?filename=%s -o /tmp/%s'  % (pkg, pkg)
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        print(" > Downloading %s ... Failed" % pkg)
        sys.exit(1)
    print_status('Downloading %s' % pkg, 'OK')
    return '/tmp/%s' % pkg


def check_docker(host_os):
    # Check that DockerCE is Installed
    if  check_host_pkg_installed(host_os, 'docker-ce') and \
        check_host_pkg_installed(host_os, 'docker-ce-cli'):
        print_status('DockerCE Installation', 'OK')
    else:
        print_status('DockerCE Installation', 'Update Required')        
        print(' > Please install DockerCE using the following documentation and relaunch the script:')
        print(' >   [CENTOS] https://docs.docker.com/install/linux/docker-ce/centos/')
        print(' >   [UBUNTU] https://docs.docker.com/install/linux/docker-ce/ubuntu/')
        sys.exit(1)
        
    # Check that DockerCE is correctly configured
    ret, out, err = exec_cmd_with_ret_output('groups $USER | grep docker')
    if ret:
        print_status('DockerCE Configuration', 'Update Required')        
        print(' > Please configure DockerCE using the following documentation and relaunch the script:')
        print(' >   https://docs.docker.com/install/linux/linux-postinstall/')
        sys.exit(1)
    else:
        print_status('DockerCE Configuration', 'OK')


def update_os_kernel(host_os):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get update -y kernel'
    elif 'centos' in host_os:
        cmd = 'sudo yum update -y kernel'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        print(out)
        print(err)
        print('[ERROR] Kernel OS update')
        sys.exit(1)


def host_reboot(cold=False):
    txt_reboot = " > Packages install/update completed, please reboot your server and relaunch this script."
    txt_halt = " > Packages install/update completed, please do a cold reboot of your server and relaunch this script."
    cmd = 'halt' if cold else 'reboot'
    txt = txt_halt if cold else txt_reboot
    print(txt)
    answer = None
    while answer not in ['y', 'n']:
        answer = raw_input(" > Do you want to %s now (y/n)? "%cmd).lower()
    if answer == 'y':
        exec_cmd_with_ret_output('sudo '+cmd)
    else:
        sys.exit(1)


def get_board_shell_flash_cmd(boardIdx):
    cmd='sudo /opt/xilinx/xrt/bin/xbutil flash scan'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    cnt=0
    host_dsa_conf=''
    host_dsa_conf=''
    for l in out.splitlines():
        if 'Card [%s]'%boardIdx in l:
            host_dsa_conf=out.splitlines()[cnt+7].strip()
            break
        cnt+=1
        
    prog_dsa=host_dsa_conf.split(',')[0]
    prog_tstamp=int(host_dsa_conf.split(',')[1][4:-1], 0)
    cmd='sudo /opt/xilinx/xrt/bin/xbutil flash -d %s -a %s -t %s' % (boardIdx, prog_dsa, prog_tstamp) 
    return cmd


def check_python_modules():
    ret, out, err = exec_cmd_with_ret_output('%s -m pip --disable-pip-version-check freeze' % sys.executable)
    installed_packages = [r.split('==')[0] for r in out.split()]
    for m in REQUIRED_PYTHON_MODULES:
        if m in installed_packages:
            print_status('Python Module %s' % m, 'Installed')
        else:
            print_status('Python Module %s' % m, 'Not Found')
            print('[ERROR] Please run "pip2/pip3 install --user %s" and relaunch this script' % m)
            sys.exit(1)


def run_setup(skip, vendor, appname):

    # Set environement variables
    os.environ['LANG'] = "en_US.UTF-8"
    os.environ['LANGUAGE'] = "en_US.UTF-8"
    os.environ['LC_COLLATE'] = "C"
    os.environ['LC_CTYPE'] = "en_US.UTF-8"
    
    # Check Python Installation
    print_status('Python Version', '%s.%s.%s'%(sys.version_info[0], sys.version_info[1], sys.version_info[2]))
    check_python_modules()
    
    # Download or Update App Catalog
    print_status('Loading App Catalog', '')
    download_appstore_catalog()
    appcatalog=yamlfile_to_dict(os.path.join(APPDEFS_FOLDER, APPLIST_FNAME))
    print_status('Loading App Catalog', 'OK')

    # Empty program arguments handling
    if not args.vendor or not args.appname:
        print(" > You must provide application vendor and name from following list:")
        for app in appcatalog['apps']:
            print_status("\t%s"%app['appvendor'].lower(), "%s"%app['appname'].lower(), 20)
        print(" > e.g: python2.7 /opt/xilinx/appstore/host_setup.py -v ngcodec -a hevc_enc_dual\n")
        sys.exit(1)
    
    appdef_path=''
    for app in appcatalog['apps']:
        if app['appvendor'].lower()==vendor.lower() and app['appname'].lower()==appname.lower():
            appdef_path=app['appdef_path']
            break
            
    if not appdef_path:
        print(" [ERROR] Unable to find application named [%s] from vendor [%s]" % (appname, vendor))
        sys.exit(1)
    print_status('Selected App', "%s - %s" % (appname, vendor))
       
    # Loading App Definition file
    appdef=yamlfile_to_dict(os.path.join(APPDEFS_FOLDER, appdef_path))  
    print_status('Loading App Definition file', 'OK')
    
    # Detect host environement
    host_os, host_os_version = get_host_env()
    host_os_full= '%s-%s' % (host_os, host_os_version)
    print_status('Detected OS', '%s'%host_os_full)
    
    # Check host kernel version
    check_kernel(host_os)
    
    # Check DockerCE Installation & Configuration
    check_docker(host_os)

    # Check if running on AWS
    running_on_aws=False
    aws_identity_file='/dev/shm/aws-identity.json'
    ret, out, err = exec_cmd_with_ret_output('curl -sm 10 http://169.254.169.254/latest/dynamic/instance-identity/document > %s' % aws_identity_file)
    if os.path.exists(aws_identity_file):
        instancedef=yamlfile_to_dict(aws_identity_file)
        if instancedef:
            print_status('Running on','AWS')
            print_status('FPGA Board', instancedef['instanceType'])
            running_on_aws=True
    else:
        print_status('Running on','On-Premise')

    # List FPGA Boards using lspci (XRT not needed)
    if running_on_aws:
        lspci_boards=[instancedef['instanceType']]
    else:
        lspci_boards=fpga_board_list()
    if not lspci_boards:
        print(" [ERROR] No FPGA Board Detected. you need at least one FPGA board to use this application.")
        sys.exit(1)
    
    # Check Host Compatibility (OS, FPGA Boards)
    if not host_os_full in appdef['Supported']['os']:
        print(" [ERROR] Operating System [%s] not supported" % host_os_full)
        sys.exit(1)
    print_status('OS Compatibility', 'OK')
    if not any(item in lspci_boards for item in appdef['Supported']['boards']):
        print(" [ERROR] Boards %s not supported by this application" % lspci_boards)
        sys.exit(1)
    print_status('FPGA Board Compatibility', 'OK')
    
    # Board Model Selection
    board_model_idx=0
    lspci_boards = list(set(lspci_boards).intersection(appdef['Supported']['boards']))
    if len(lspci_boards) > 1:
        print("\n > Found %s board models" % len(lspci_boards))
        for i in range(0,len(lspci_boards)):
            print("\t[%s]: %s" % (i, lspci_boards[i]))
        board_model_idx = int(raw_input(" > Please select the model to use: "))
    print_status('Selected board model', '%s'%lspci_boards[board_model_idx])
    
    # Find suitable configuration
    selected_conf=None
    for conf in appdef['HostSetupConfiguration']:
        if host_os_full == conf['os'] and lspci_boards[board_model_idx] in conf['board']:
            print_status('Suitable App Configuration', 'OK')
            selected_conf=conf
            break
    if not selected_conf:
        print_status('Suitable App Configuration', 'Not Found')
        sys.exit(1)
        
    # Check Installed versions of XRT against selected_conf['xrt_package']
    check_xrt(host_os, conf['xrt_package'], selected_conf)
    
    # Check Installed versions of Host DSA against selected_conf['dsa_package']
    if not running_on_aws:
        check_host_dsa(host_os, selected_conf)
    
    # Detect FPGA environement
    boards, shells = get_fpga_env(host_os, running_on_aws)
    
    # Board Selection
    board_idx=0
    if len(boards) > 1:
        print("\n > Found %s boards" % len(boards))
        for i in range(0,len(boards)):
            print("\t[%s]: %s (%s)" % (i, boards[i], shells[i]))
        board_idx = int(raw_input(" > Please select the one to use: "))
    print_status('Selected board', '%s %s %s' % (board_idx, boards[board_idx], shells[board_idx]))
    
    # Check Board DSA
    if not running_on_aws:
        check_board_shell(board_idx)
                
    # Check Access Key
    homedir = os.environ['HOME']
    if os.path.exists(os.path.join(homedir, 'cred.json')):
        print_status('Access Key Check', 'OK')
    else:
        print_status('Access Key Check', 'Not Found')
        print(" [!] Please copy your access key in %s and run this script again" % os.path.join(homedir, 'cred.json'))
        return
        
    # FPGA Device Identification script
    if not os.path.exists('/opt/xilinx/appstore'):
        exec_cmd_with_ret_output('sudo mkdir /opt/xilinx/appstore')
    exec_cmd_with_ret_output('sudo chmod -R 777 /opt/xilinx/appstore')
    if(running_on_aws):
        shutil.copyfile(SETENV_SCRIPT_AWS, '/opt/xilinx/appstore/set_env_aws.sh')
    else:
        shutil.copyfile(SETENV_SCRIPT, '/opt/xilinx/appstore/set_env.sh')
    print_status('FPGA Device Identification Script', 'Created')
    
    # Update Docker Commands
    username = getpass.getuser()
    pullCmd=appdef['DockerCmds'][lspci_boards[board_model_idx]]['pull']
    runCmd=appdef['DockerCmds'][lspci_boards[board_model_idx]]['run'].replace('$USER', username)
    
    # Create runapp script
    run_app_fname="runapp_%s_%s.sh" % (vendor.lower(), appname.lower())
    run_app_path=os.path.join('/opt', 'xilinx', 'appstore', run_app_fname)
    txt= '#!/bin/bash\n' \
    'if [ ! "$BASH_VERSION" ] ; then echo "Please do not use sh to run this script ($0), just execute it directly" 1>&2; exit 1; fi\n' \
    'source /opt/xilinx/appstore/set_env%s.sh\n' \
    '%s\n' \
    '%s\n' % ('_aws' if running_on_aws else '', pullCmd, runCmd)
    with open(run_app_path,"w+") as f:
        f.write(u'%s' % txt)
        
    exec_cmd_with_ret_output('sudo chmod +x %s' % run_app_path)
    print_status('Run App Script', 'Created')

    print("\n > Your host is configured correctly, you can run the application using the following commands:")
    if(running_on_aws):
        print("\tsource /opt/xilinx/appstore/set_env_aws.sh")
    else:
        print("\tsource /opt/xilinx/appstore/set_env.sh")
    print("\t%s"%pullCmd)
    print("\t%s"%runCmd)
    print("\n > Note: You can also use the following convenient bash script to run these commands:")
    print(" > %s\n\n"%run_app_path)



if __name__ == '__main__':

    if (sys.version_info[0], sys.version_info[1]) != REQ_PYTHON:
        sys.exit("Python %s.%s is required.\n" % REQ_PYTHON)
    
    print("  -------------------------------------------")
    print(" | Xilinx Host Setup Script for Alveo Boards |")
    print("  -------------------------------------------")
    print(" Welcome to the Xilinx Host Setup Script for Alveo Boards.\n")
    print(" This script will guide the setup of your host for running one of the Xilinx AppStore FPGA application\n")
    print_status('Host Setup Script Version', SCRIPT_VERSION)
    
    # Parse the arguments
    option = argparse.ArgumentParser()
    option.add_argument('--vendor', '-v', dest="vendor", type=str, default=None,
                        required=False, help="App Vendor")
    option.add_argument('--appname', '-a', dest="appname", type=str, default=None,
                        required=False, help="App Name")
    option.add_argument('--skip', '-s', dest="skip", action="store_true", 
                        help="Skip questions and use default value")
    args = option.parse_args()
                
    sys.exit(run_setup(skip=args.skip, vendor=args.vendor, appname=args.appname))
