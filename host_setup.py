# coding=utf-8
"""

"""
import os, sys, shutil, json, argparse, getpass
from subprocess import Popen, PIPE, STDOUT, run,check_call
import locale, yaml

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))
GIT_REPO_XX_APPSTORE="https://github.com/Accelize/xilinx_appstore_appdefs.git"
APPDEFS_FOLDER=os.path.join(SCRIPT_PATH, "xilinx_appstore_appdefs")
APPLIST_FNAME="applist.json"
SETENV_SCRIPT=os.path.join(SCRIPT_PATH, 'xilinx_appstore_env.sh')
host_dependencies_ubuntu = 'curl linux-headers'
host_dependencies_centos = 'curl epel-release kernel-headers kernel-devel'

def parse_value(key_value):
    """
    Parse os-release value

    Args:
        key_value (str): key="value"

    Returns:
        str: Value
    """
    return key_value.split('=')[1].rstrip().strip('""').lower()
    

def pip_install(package):
    check_call(['sudo', sys.executable, '-m', 'pip', 'install', package])


def curl_dwnld(url, output):
    import pycurl
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    with open(output, 'w') as f:
        c.setopt(c.WRITEFUNCTION, f.write)
        c.perform()    

def print_status(text, status, fulllength=40):
    padding_size = fulllength - len(text)
    print(f" > {text} {'.'*padding_size} {status}")


def jsonfile_to_dict(filename):
    with open(filename, 'r', encoding="utf-8") as json_file:
        return json.load(json_file)
        

def yamlfile_to_dict(filename):
    with open(filename, 'r', encoding="utf-8") as yaml_file:
        return yaml.safe_load(yaml_file)
        

def dict_to_yamlfile(d, filename):
    with open(filename, 'w', encoding="utf-8") as yaml_file:
        yaml.dump(d, yaml_file)


def dict_pretty_print(in_dict):
    print(json.dumps(in_dict, sort_keys=True, indent=4))
    

def exec_cmd_with_ret_output(cmd, path='.'): 
    try:
        cmd = 'cd %s && %s' %(path, cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, universal_newlines=True)
        stdout, stderr = p.communicate()
        return p.returncode, stdout, stderr
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
                host_os = parse_value(line).lower()
            if host_os_version and host_os:
                break
    
    if  host_os is 'ubuntu' and host_os_version not in ['16.04','18.04'] or \
        host_os is 'centos' and host_os_version not in ['7'] or \
        host_os is None:
        print(f" [ERROR] Your Operating System is nt supported.\nSupported OS: CentOS 7, Ubuntu 16.04 and Ubuntu 18.04")
        sys.exit(1)
    print_status('Detected OS', f'{host_os}')
    return host_os
    
def get_fpga_env(host_os):
    # Get FPGA Boards & Shells
    ret, out, err = exec_cmd_with_ret_output("/opt/xilinx/xrt/bin/xbutil list | grep Found | cut -d' ' -f4")
    nbBoardsFound = out.strip()
    if nbBoardsFound == '': nbBoardsFound='0'
    print_status('Board(s) Found', f'{nbBoardsFound}')
    if nbBoardsFound == '0': 
        print(f" [ERROR] No FPGA Board Detected. you need at least one FPGA board to use this application.")
        sys.exit(1)
        
    ret, out, err = exec_cmd_with_ret_output("/opt/xilinx/xrt/bin/xbutil list | grep Found | cut -d' ' -f6")
    nbBoardsUsable = out.strip()
    print_status('Board(s) Usable', f'{nbBoardsUsable}')
    if nbBoardsUsable == '0': 
        print(f" [ERROR] Deployment Target Platform Not Installed")
        sys.exit(1)
    
    boards=[]
    shells=[]
    ret, out, err = exec_cmd_with_ret_output('/opt/xilinx/xrt/bin/xbutil list')
    for line in out.splitlines():
        if 'xilinx_' in line: 
            shells.append(line.split(' ')[-1])
            boards.append(line.split(' ')[-1].split('_')[1])
    print_status('Detected Boards', f'{boards}')
    print_status('Detected Shells', f'{shells}')
    
    return boards, shells


def dsa_format(dsa):
    char_list=['-', ' ', '.']
    for c in char_list:
        dsa=dsa.replace(c,'_')
    return dsa


def check_xrt(host_os, target_version):
    if not check_host_pkg_installed(host_os, 'xrt'):
        return True
     
    xrt_version = get_xrt_version(host_os)
    if not xrt_version: 
        return True
    print_status('Detected XRT', f'{xrt_version}')
    
    if xrt_version in target_version :
        print_status('XRT Version Check', f'OK ({xrt_version})')
        return False
    print_status('XRT Version Check', 'Failed')
    return True

 
def check_host_dsa(host_os, conf_pkg):
    pkg_name=conf_pkg.split('-')[0]+'-'+conf_pkg.split('-')[1]+'-'+conf_pkg.split('-')[2]
    pkg_vers=conf_pkg.split('-')[3]
   
    if 'centos' in host_os: 
        ret, out, err = exec_cmd_with_ret_output(f'sudo yum list installed | grep {pkg_name} | grep {pkg_vers} > /dev/null 2>&1')
    else:
        ret, out, err = exec_cmd_with_ret_output(f'sudo apt list --installed | grep {pkg_name} | grep {pkg_vers} > /dev/null 2>&1')

    if ret:
        print_status('Board Shell [HOST] Version Check', f'Failed ({pkg_name}-{pkg_vers})')
        return True 
    print_status('Board Shell [HOST] Version Check', f'OK ({pkg_name}-{pkg_vers})')    
    return False


def check_docker(host_os):
    if check_host_pkg_installed(host_os, 'docker-ce'):
        print_status('DockerCE  Check', 'OK')
        return False
    print_status('DockerCE  Check', 'Failed')
    return True


def check_dependencies(host_os):
    deps= host_dependencies_ubuntu if 'ubuntu' in host_os else host_dependencies_centos
    for dep in deps.split(' '):
        if not check_host_pkg_installed(host_os, dep):
            print_status('OS  Dependency Package(s)', 'Failed')
            return True
    print_status('OS  Dependency Package(s)', 'OK')
    return False


def check_kernel():
    if os.path.exists(os.path.join('/lib','modules', os.uname()[2], 'build')):
        print_status('Kernel Version Check', 'OK')
        return False
    print_status('Kernel Version Check', 'Failed')
    return True


def check_board_shell(boardIdx):
    cmd='sudo /opt/xilinx/xrt/bin/xbutil flash scan'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    cnt=0
    for l in out.splitlines():
        if f'Card [{boardIdx}]' in l:
            if(out.splitlines()[cnt+5].strip() == out.splitlines()[cnt+7].strip()):
                print_status('Board Shell Host vs. FPGA', 'OK')
                return False
        cnt+=1     
    print_status('Board Shell Host vs. FPGA', 'Failed')
    return True


def check_host_pkg_installed(host_os, pkg):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt list --installed | grep '+ pkg
    elif 'centos' in host_os:
        cmd = 'sudo yum list installed | grep '+ pkg
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        return False
    return True


def host_pkg_install(host_os, packages):    
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get install -y '+ packages + '> /dev/null 2>&1'
    elif 'centos' in host_os:
        cmd = 'sudo yum install -y '+ packages + '> /dev/null 2>&1'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise

 
def host_pkg_remove(host_os, packages):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get remove -y '+ packages + '> /dev/null 2>&1'
    elif 'centos' in host_os:
        cmd = 'sudo yum remove -y '+ packages + '> /dev/null 2>&1'
    run(cmd, shell=True)

def host_pkg_download(pkg):
    print_status(f'Downloading {pkg}', '')
    cmd = f'curl -sL https://www.xilinx.com/bin/public/openDownload?filename={pkg} -o /tmp/{pkg}'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        print(f" > Downloading {pkg} ... Failed")
        raise
    print_status(f'Downloading {pkg}', 'OK')
    return f'/tmp/{pkg}'


def install_dependencies(host_os):
    if 'ubuntu' in host_os:
        host_pkg_install(host_os, host_dependencies_ubuntu)
    elif 'centos' in host_os:
        host_pkg_install(host_os, host_dependencies_centos)


def install_DockerCE():
    cmd = 'curl -fsSL https://get.docker.com | sudo sh'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise


def configure_DockerCE():
    cmd = 'sudo mkdir -p /etc/docker && echo \'{\"max-concurrent-downloads\": 1}\' | sudo tee -a /etc/docker/daemon.json && sudo systemctl restart docker && sudo systemctl enable docker && sudo usermod -aG docker $USER'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise


def update_os_kernel(host_os):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get update -y kernel'
    elif 'centos' in host_os:
        cmd = 'sudo yum update -y kernel'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise


def host_reboot(cold=False):
    cmd = 'halt' if cold else 'reboot'
    answer = None
    while answer not in ['y', 'n']:
        answer = input(f" > Do you want to {cmd} now (y/n)? ").lower()
    if answer == 'y':
        run('sudo '+cmd, shell=True)
    else:
        sys.exit(1)


def board_shell_flash(boardIdx):
    cmd='sudo /opt/xilinx/xrt/bin/xbutil flash scan'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    cnt=0
    host_dsa_conf=''
    for l in out.splitlines():
        if f'Card [{boardIdx}]' in l:
            host_dsa_conf=out.splitlines()[cnt+7].strip()
            break
        cnt+=1
        
    prog_dsa=host_dsa_conf.split(',')[0]
    prog_tstamp=int(host_dsa_conf.split(',')[1][4:-1], 0)
    cmd=f'sudo /opt/xilinx/xrt/bin/xbutil flash -d {boardIdx} -a {prog_dsa} -t {prog_tstamp}'
    run(cmd, shell=True)


def update_host_env(host_os, update_kernel, dependencies, install_docker=False):
    print(f"")
    print(f" > Packages install/update:")
    if dependencies: print(f" > \tDependencies (curl, ...)")
    if update_kernel: print(f" > \tKernel Update")
    print(f" > \tDocker CE")
    
    answer = None
    while answer not in ['y', 'n']:
        answer = input(f" > Start update process (y/n)? ").lower()
    if answer == 'y':
        if dependencies:
            print_status('Updating Dependencies', '')            
            install_dependencies(host_os)       
            print_status('Updating Dependencies', 'Done')
        if update_kernel:
            print_status('Updating Kernel', '')
            update_os_kernel(host_os)     
            print_status('Updating Kernel', 'Done')
        
        print_status('Updating DockerCE', '')
        if install_docker:
            install_DockerCE()  
        configure_DockerCE()        
        print_status('Updating DockerCE', 'Done')        
        
        print(f" > Packages install/update completed, please reboot your server and relaunch this script.")
        host_reboot(cold=False)
    else:
        sys.exit(0)


def update_fpga_env(host_os, selected_conf, xrt_outdated, host_dsa_outdated):
    print(f"")
    print(f" > Packages install/update:")
    if xrt_outdated: print(f" > \tXRT ({selected_conf['xrt_package']})")
    if host_dsa_outdated: print(f" > \tBoard Shell [HOST] ({selected_conf['dsa_package']})")

    answer = None
    while answer not in ['y', 'n']:
        answer = input(f" > Start update process (y/n)? ").lower()
    if answer == 'y':
        if xrt_outdated:
            print_status('Updating XRT', '')
            host_pkg_remove(host_os, 'xrt')
            pkg_path=host_pkg_download(selected_conf['xrt_package'])
            host_pkg_install(host_os, pkg_path)
            print_status('Updating XRT', 'Done')

        # Check Installed versions of Host DSA against selected_conf['dsa_package']
        if host_dsa_outdated:
            print_status('Updating Board Shell [HOST]', '')
            pkg_path=host_pkg_download(selected_conf['dsa_package'])
            host_pkg_install(host_os, pkg_path)
            print_status('Updating Board Shell [HOST]', 'Done')
            
        # Reboot
        print(f" > Packages install/update completed, please reboot your server and relaunch this script.")
        host_reboot(cold=False)
    else:
        sys.exit(0)  
        
          
def update_board_dsa(board_idx):
    print(f"")
    print(f" > Packages install/update:")
    print(f" > \tBoard Shell [FPGA])")
    
    answer = None
    while answer not in ['y', 'n']:
        answer = input(f" > Start update process (y/n)? ").lower()
    if answer == 'y':
        print_status('Programming Board Shell [FPGA]', '')
        board_shell_flash(board_idx)
        print_status('Programming Board Shell [FPGA]', 'Done')
        
        print(f" > Packages install/update completed, please do a cold reboot of your server and relaunch this script.")
        host_reboot(cold=True)
    else:
        sys.exit(0)


def run_setup(skip, vendor, appname):
    # Loading App Catalog file
    appcatalog=jsonfile_to_dict(os.path.join(APPDEFS_FOLDER, APPLIST_FNAME))
    print_status('Loading App Catalog', 'OK')
    
    appdef_path=''
    for app in appcatalog['apps']:
        if app['appvendor'].lower()==vendor.lower() and app['appname'].lower()==appname.lower():
            appdef_path=app['appdef_path']
            break
            
    if not appdef_path:
        print(f" [ERROR] Unable to find application named [{appname}] from vendor [{vendor}]")
        sys.exit(1)
    print_status('Selected App', f"{vendor} - {appname}")
       
    # Loading App Definition file
    appdef=jsonfile_to_dict(os.path.join(APPDEFS_FOLDER, appdef_path))  
    print_status('Loading App Definition file', 'OK')
    
    # Detect host environement
    host_os = get_host_env()
    
    # Check host updates needed
    dep_updt=check_dependencies(host_os)
    krn_updt=check_kernel()
    dkr_updt=check_docker(host_os)
    if dkr_updt or krn_updt or dep_updt:
        update_host_env(host_os, krn_updt, dep_updt, dkr_updt)
        
    # List FPGA Boards using lspci (XRT not needed)
    lspci_boards=fpga_board_list()
    if not lspci_boards:
        print(f" [ERROR] No FPGA Board Detected. you need at least one FPGA board to use this application.")
        sys.exit(1)
    
    # Check Host Compatibility (OS, FPGA Boards)
    if not host_os in appdef['Supported']['os']:
        print(f" [ERROR] Operating System {host_os}] not supported")
        sys.exit(1)
    print_status('OS Compatibility', 'OK')
    if not any(item in lspci_boards for item in appdef['Supported']['boards']):
        print_status('FPGA Board Compatibility', 'Failed')
        print(f" [ERROR] Boards {lspci_boards} not supported by this application")
        sys.exit(1)
    print_status('FPGA Board Compatibility', 'OK')
    
    # Board Model Selection
    board_model_idx=0
    lspci_boards = list(set(lspci_boards).intersection(appdef['Supported']['boards']))
    if len(lspci_boards) > 1:
        print(f"\n > Found {len(lspci_boards)} board models")
        for i in range(0,len(lspci_boards)):
            print(f"\t[{i}]: {lspci_boards[i]}")
        board_model_idx = int(input(" > Please select the model to use: "))
    print(f" > Selected board model: {lspci_boards[board_model_idx]}\n")
    print_status('Selected board model', f'{lspci_boards[board_model_idx]}')
    
    # Find suitable configuration
    selected_conf=None
    for conf in appdef['HostSetupConfiguration']:
        if host_os == conf['os'] and lspci_boards[board_model_idx] in conf['board']:
            print_status('Suitable App Configuration', 'OK')
            selected_conf=conf
    if not selected_conf:
        print_status('Suitable App Configuration', 'Failed')
        sys.exit(1)
        
    # Check Installed versions of XRT against selected_conf['xrt_package']
    xrt_outdated = check_xrt(host_os, conf['xrt_package'])
    host_dsa_outdated = check_host_dsa(host_os, selected_conf['dsa_package'])
    if xrt_outdated or host_dsa_outdated:
        update_fpga_env(host_os, selected_conf, xrt_outdated, host_dsa_outdated)
    
    # Detect FPGA environement
    boards, shells = get_fpga_env(host_os)
    
    # Board Selection
    board_idx=0
    if len(boards) > 1:
        print(f"\n > Found {len(boards)} boards")
        for i in range(0,len(boards)):
            print(f"\t[{i}]: {boards[i]} ({shells[i]})")
        board_idx = int(input(" > Please select the one to use: "))
    print_status('Selected board', f'{board_idx}: {boards[board_idx]} {shells[board_idx]}')
    
    # Check Board DSA
    board_dsa_outdated=check_board_shell(board_idx)
    if board_dsa_outdated:
        update_board_dsa(board_idx)
                
    # Check Access Key
    homedir = os.environ['HOME']
    if os.path.exists(os.path.join(homedir, 'cred.json')):
        print_status('Access Key Check', 'OK')
    else:
        print_status('Access Key Check', 'Failed')
        print(f" [!] Please copy your access key in {os.path.join(homedir, 'cred.json')} and run this script again")
        return
        
    # FPGA Device Identification script
    if not os.path.exists('/opt/xilinx/appstore'):
        run('sudo mkdir /opt/xilinx/appstore', shell=True)
    run('sudo chmod -R 777 /opt/xilinx/appstore', shell=True)
    shutil.copyfile(SETENV_SCRIPT, '/opt/xilinx/appstore/set_env.sh')
    print_status('FPGA Device Identification Script', 'Created')
    
    # Update Docker Commands
    username = getpass.getuser()
    pullCmd=appdef['DockerCmds']['pull']
    runCmd=appdef['DockerCmds']['run'].replace('$USER', username)
    
    # Create runapp script
    run_app_fname=f"runapp_{vendor.lower()}_{appname.lower()}.sh"
    run_app_path=os.path.join('/opt', 'xilinx', 'appstore', run_app_fname)
    with open(run_app_path,"w+") as f:
        f.write('#!/bin/bash\n')
        f.write('source /opt/xilinx/appstore/set_env.sh\n\n')
        f.write(f"{pullCmd}\n")
        f.write(f"{runCmd}\n")
    run(f'sudo chmod +x {run_app_path}', shell=True)
    print_status('Run App Script', 'Created')

    print(f"\n > Your host is configured correctly, you can start to use the aplication:")
    print(f" > A. By using the following commands:")
    print(f"\tsource /opt/xilinx/appstore/set_env.sh")
    print(f"\t{pullCmd}")
    print(f"\t{runCmd}")
    print(f" > B. By using convenient script: {run_app_path}\n\n")



if __name__ == '__main__':

    print(f"  -------------------------------------------")
    print(f" | Xilinx Host Setup Script for Alveo Boards |")
    print(f"  -------------------------------------------")
    print(f" Welcome to the Xilinx Host Setup Script for Alveo Boards.\n")
    print(f" This script will guide to setup your host for running one of the Xilinx AppStore FPGA application\n")
    
    # Parse the arguments
    option = argparse.ArgumentParser()
    option.add_argument('--vendor', '-v', dest="vendor", type=str, default=None,
                        required=False, help="App Vendor")
    option.add_argument('--appname', '-a', dest="appname", type=str, default=None,
                        required=False, help="App Name")
    option.add_argument('--skip', '-s', dest="skip", action="store_true", 
                        help="Skip questions and use default value")
    args = option.parse_args()
            
    if not args.vendor or not args.appname:
        print(f" > You must provide application vendor and name from following list:")
        appcatalog=jsonfile_to_dict(os.path.join(APPDEFS_FOLDER, APPLIST_FNAME))
        for app in appcatalog['apps']:
            print_status(f"\t{app['appvendor'].lower()}", f"{app['appname'].lower()}", 20)
        print(f" > e.g: python3 host_setup.py -v ngcodec -a hevc_enc_dual\n")
        sys.exit(1)
    
    sys.exit(run_setup(skip=args.skip, vendor=args.vendor, appname=args.appname))
