# coding=utf-8
"""

"""
import os, sys, shutil, json, argparse, getpass
from subprocess import Popen, PIPE, STDOUT

GIT_REPO_XX_APPSTORE="https://github.com/Accelize/xilinx_appstore_appdefs.git"
APPDEFS_FOLDER="xilinx_appstore_appdefs"
APPLIST_FNAME="applist.json"
host_dependencies_ubuntu = 'curl linux-headers'
host_dependencies_centos = 'curl epel-release kernel-headers kernel-devel'


def print_status(text, status):
    padding_size = 40 - len(text)
    print(f" > {text} {'.'*padding_size} {status}")


def jsonfile_to_dict(filename):
    with open(filename, 'r') as json_file:
        return json.load(json_file)


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


def get_xrt_version(host_os):
    xrt=None
    if 'centos' in host_os.lower():
        ret, out, err = exec_cmd_with_ret_output("sudo yum info xrt | grep Version | cut -d ':' -f2")
        xrt=out.strip()
        
    if 'ubuntu' in host_os.lower():
        ret, out, err = exec_cmd_with_ret_output("sudo apt list --installed | grep xrt | tail -n1 | cut -d' ' -f2")
    return xrt


def  get_host_env():
    # Get OS
    import platform
    host_os=None
    if 'ubuntu-18.04' in platform.platform(): host_os='ubuntu-18.04'
    if 'ubuntu-16.04' in platform.platform(): host_os='ubuntu-16.04'
    if 'centos' in platform.platform(): host_os='centos'
    print_status('Detected OS', f'{host_os}')
    return host_os
    
def  get_fpga_env(host_os):
    
    # Get XRT version
    xrt_version = get_xrt_version(host_os).split('-')[0]
    if not xrt_version: 
        print(f" [ERROR] No XRT Installed. Please install Xilinx XRT package and run the script again.")
        sys.exit(0)
    print_status('Detected XRT', f'{xrt_version}')

    # Get FPGA Boards & Shells
    ret, out, err = exec_cmd_with_ret_output("/opt/xilinx/xrt/bin/xbutil list | grep Found | cut -d' ' -f4")
    nbBoardsFound = out.strip()
    if nbBoardsFound == '': nbBoardsFound='0'
    print_status('Board(s) Found', f'{nbBoardsFound}')
    if nbBoardsFound == '0': 
        print(f" [ERROR] No FPGA Board Detected. you need at least one FPGA board to use this application.")
        sys.exit(0)
        
    ret, out, err = exec_cmd_with_ret_output("/opt/xilinx/xrt/bin/xbutil list | grep Found | cut -d' ' -f6")
    nbBoardsUsable = out.strip()
    print_status('Board(s) Usable', f'{nbBoardsUsable}')
    if nbBoardsUsable == '0': 
        print(f" [ERROR] Deployment Target Platform Not Installed")
        sys.exit(0)
    
    boards=[]
    shells=[]
    ret, out, err = exec_cmd_with_ret_output('/opt/xilinx/xrt/bin/xbutil list')
    for line in out.splitlines():
        if 'xilinx_' in line: 
            shells.append(line.split(' ')[-1])
            boards.append(line.split(' ')[-1].split('_')[1])
    print_status('Detected Boards', f'{boards}')
    print_status('Detected Shells', f'{shells}')
    
    return boards, shells, xrt_version


def dsa_format(dsa):
    char_list=['-', ' ', '.']
    for c in char_list:
        dsa=dsa.replace(c,'_')
    return dsa


def check_xrt(current_ver, target_version):
    if current_ver in target_version :
        print_status('XRT Version Check', f'OK ({current_ver})')
        return None
    print_status('XRT Version Check', 'Failed')
    return target_version

 
def check_dsa(current_ver, target_version):
    if current_ver in target_version :
        print_status('Board Shell [HOST] Version Check', f'OK ({current_ver})')
        return None
    print_status('Board Shell [HOST] Version Check', 'Failed')
    return target_version


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
            print_status('OS  Dependency Package(s)', 'OK')
            return True
    print_status('OS  Dependency Package(s)', 'Failed')
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
        False
    return True


def host_pkg_install(host_os, packages):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get install -y '+ packages
    elif 'centos' in host_os:
        cmd = 'sudo yum install -y '+ packages
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise

 
def host_pkg_remove(host_os, packages):
    if 'ubuntu' in host_os:
        cmd = 'sudo apt-get remove -y '+ packages
    elif 'centos' in host_os:
        cmd = 'sudo yum remove -y '+ packages
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise


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
    cmd = 'curl -fsSL https://get.docker.com | sudo sh && sudo systemctl start docker && sudo systemctl enable docker && sudo usermod -aG docker $USER'
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise
        
def update_kernel(host_os):
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
        ret, out, err = exec_cmd_with_ret_output('sudo '+cmd)
        if ret:
            raise


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
    ret, out, err = exec_cmd_with_ret_output(cmd)
    if ret:
        raise


def update_host_env(host_os, update_kernel, dependencies, install_docker=False):
    print(f"")
    print(f" > Packages install/update:")
    if dependencies: print(f" > \tDependencies (curl, ...)")
    if update_kernel: print(f" > \tKernel Update")
    if install_docker: print(f" > \tDocker CE")
    
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
            host_pkg_install(host_os)     
            print_status('Updating Kernel', 'Done')
        if install_docker:
            print_status('Updating DockerCE', '')
            install_DockerCE()        
            print_status('Updating DockerCE', 'Done')        
        
        print(f" > Packages install/update completed, please reboot your server")
        host_reboot(cold=False)
    else:
        sys.exit(0)



def update_host_env(host_os, board_idx, update_xrt=None, update_dsa=None, update_boardshell=False):
    print(f"")
    print(f" > Packages install/update:")
    if update_xrt: print(f" > \tXRT ({update_xrt})")
    if update_dsa: print(f" > \tBoard Shell [HOST] ({update_dsa})")
    if update_boardshell: print(f" > \tBoard Shell [FPGA])")
    
    answer = None
    while answer not in ['y', 'n']:
        answer = input(f" > Start update process (y/n)? ").lower()
    if answer == 'y':
        if update_xrt:
            print_status('Updating XRT', '')
            host_pkg_remove(host_os, 'xrt')
            pkg_path=host_pkg_download(update_xrt)
            host_pkg_install(host_os, pkg_path)
            print_status('Updating XRT', 'Done')
        if update_dsa:
            print_status('Updating Board Shell [HOST]', '')
            pkg_path=host_pkg_download(update_dsa)
            host_pkg_install(host_os, pkg_path)
            board_shell_flash(board_idx)
            print_status('Updating Board Shell [HOST]', 'Done')
        if update_boardshell:
            print_status('Programming Board Shell [FPGA]', '')
            board_shell_flash(board_idx)
            print_status('Programming Board Shell [FPGA]', 'Done')
        
        if update_dsa or update_boardshell:
            print(f" > Packages install/update completed, please do a cold reboot of your server")
            host_reboot(cold=True)
        else:
            print(f" > Packages install/update completed, please reboot your server")
            host_reboot(cold=False)
    else:
        sys.exit(0)


def run_setup(skip, vendor, appname):
    # Loading App Catalog file
    print(f" > Loading App Catalog...")
    appcatalog=jsonfile_to_dict(os.path.join(APPDEFS_FOLDER, APPLIST_FNAME))
    
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
    print(f" > Loading App Definition file...")
    appdef=jsonfile_to_dict(os.path.join(APPDEFS_FOLDER, appdef_path))
    
    # Detect host environement
    host_os = get_host_env()
    dep_updt=check_dependencies(host_os)
    krn_updt=check_kernel()
    dkr_updt=check_docker(host_os)
    if dkr_updt or krn_updt or dep_updt:
        update_host_env(host_os, krn_updt, dep_updt, dkr_updt)
    
    # Detect FPGA environement
    boards, shells, xrt_version = get_fpga_env(host_os)
    
    # Check Host Compatibility (OS, FPGA Boards)
    if not host_os in appdef['Supported']['os']:
        print(f" [ERROR] Operating System {host_os}] not supported")
        sys.exit(1)
    print_status('OS Compatibility', 'OK')
    if not any(item in boards for item in appdef['Supported']['boards']):
        print(f" [ERROR] Boards {boards} not supported by this application")
        sys.exit(1)
    print_status('FPGA Board Compatibility', 'OK')
    
    # Board Selection
    board_idx=0
    if len(boards) > 1:
        print(f"\n > Found {len(boards)} boards")
        for i in range(0,len(boards)):
            print(f"\t[{i}]: {boards[i]} ({shells[i]})")
        board_idx = int(input(" > Please select the one to use: "))
    print(f" > Selected board {board_idx}: {boards[board_idx]} {shells[board_idx]}\n")

    # Find suitable configuration
    for conf in appdef['HostSetupConfiguration']:
        if host_os == conf['os'] and boards[board_idx] in conf['board']:
            xrt_updt=check_xrt(xrt_version, conf['xrt_package'])
            dsa_updt=check_dsa(shells[board_idx], dsa_format(conf['dsa_package']))
            brd_updt=check_board_shell(board_idx)
            
            if xrt_updt or dsa_updt or brd_updt:
                update_fpga_env(host_os, board_idx, xrt_updt, dsa_updt, brd_updt)
                
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
        exec_cmd_with_ret_output('sudo mkdir /opt/xilinx/appstore ')
    exec_cmd_with_ret_output('sudo chmod -R 777 /opt/xilinx/appstore')
    shutil.copyfile('xilinx_appstore_env.sh', '/opt/xilinx/appstore/set_env.sh')
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
    print_status('Run App Script', 'Created')

    print(f"\n > Your host is configured correctly, you can start to use the aplication:")
    print(f" > A. By using convenient script: {run_app_path}")
    print(f" > B. By using the following commands:")
    print(f"\tsource /opt/xilinx/appstore/set_env.sh")
    print(f"\t{pullCmd}")
    print(f"\t{runCmd}\n\n")


def run_app(appvendor, appname):
    run_app_fname=f"runapp_{appvendor.lower()}_{appname.lower()}.sh"
    run_app_path=os.path.join('/opt', 'xilinx', 'appstore', run_app_fname)
    if not os.path.exists(run_app_path):
        print(f" [ERROR] Unable to find run app script [{run_app_path}]")
        sys.exit(1)
        
    exec_cmd_with_ret_output(run_app_path)
    

if __name__ == '__main__':

    print(f"  -------------------------------------------")
    print(f" | Xilinx Host Setup Script for Alveo Boards |")
    print(f"  -------------------------------------------")
    print(f"Welcome to the Xilinx Host Setup Script for Alveo Boards.\nThis script will guide to setup your host for running one of the Xilinx AppStore FPGA application\n")
    
    # Parse the arguments
    option = argparse.ArgumentParser()
    option.add_argument('--vendor', '-v', dest="vendor", type=str, default="UNKNOWN",
                        required=False, help="App Vendor")
    option.add_argument('--appname', '-a', dest="appname", type=str, default="UNKNOWN",
                        required=False, help="App Name")
    option.add_argument('--run', '-r', dest="run", action="store_true", 
                        help="Run the AppStore Application")
    option.add_argument('--skip', '-s', dest="skip", action="store_true", 
                        help="Skip questions and use default value")
    args = option.parse_args()
    
    if args.run:
        sys.exit(run_app(args.vendor, args.appname))
    
    sys.exit(run_setup(skip=args.skip, vendor=args.vendor, appname=args.appname))
