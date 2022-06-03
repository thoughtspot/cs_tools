# Activate the CS Tools virtual environment.
#
# Written by: Nick Cooper <nicholas.cooper@thoughtspot.com>
# Last Modified: 2022/06/02
# Version: 0.3.0
#
# CHANGELOG
# v0.1.0 - INITIAL RELEASE
# v0.2.0 - activate from .bat --> .ps1
# v0.3.0 - care for py36 installs
#
$NL = [Environment]::NewLine
$SCRIPT_DIR = $PSScriptRoot
$APP_DIR = "$env:APPDATA\cs_tools"
$_ACTIVATE = "$APP_DIR\.cs_tools\Scripts\Activate"


function error ($msg) {
    # Log a warning message and exit.
    #
    # Nothing special. There's a pause in here so the user knows where they
    # might've gone wrong.
    #
    write-warning $msg
    write-host    $NL
    pause
    exit
}


function setup_venv ($install_type = 'local') {
    # Setup a virtual environment.
    #
    # The requirements are different based on if you can access the outside
    # internet or not. All packages are distributed locally alonside this
    # script, but it's possible to grab them all from PyPI and Github instead.
    # 
    # Parameters
    # ----------
    # install_type : str , default 'local'
    #   either local or remote, where to source install packages from
    #
    $python_version = (&{python -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"})
    $pip_install = "$APP_DIR\.cs_tools\Scripts\python.exe -m pip install --upgrade --no-cache-dir --force-reinstall"
    mkdir $APP_DIR -ErrorAction SilentlyContinue
    python -m venv "$APP_DIR\.cs_tools"
    & "$_ACTIVATE.ps1"

    if ( $python_version -eq '3.6' ) {
        $py = "py36-"
    }
    else {
        $py = ""
    }

    if ( $install_type -eq 'local' ) {
        Invoke-Expression "$pip_install -r $SCRIPT_DIR/reqs/" + $py + "offline-install.txt --find-links=$SCRIPT_DIR/pkgs/ --no-index"
    }
    elseif ( $install_type -eq 'remote' ) {
        Invoke-Expression "$pip_install -r $SCRIPT_DIR/reqs/" + $py + "requirements.txt"
    }
    else {
        error 'no option like $install_type, type either "local" or "remote"'
    }
}


function activate ($py_args = 'interactive') {
    # Activate the virtual environment.
    #
    # cmd switch /k instructs command prompt to issue the command and then
    # stay open (normally so you can view results). In our case, we're starting
    # a separate process for the explicit purpose of using that as our tools
    # window.
    #
    if ( $py_args -eq 'interactive' ) {
        Start powershell -ArgumentList "-ExecutionPolicy Bypass -NoExit $_ACTIVATE.ps1; cs_tools"
    }
    # TODO: augment with the ability to use in Task Scheduler.
    #       - should accept args list and pass to $_ACTIVATE appropriately.
}


if (test-path "$APP_DIR\.cs_tools\Scripts\Activate.ps1" -pathtype Leaf) {
    activate
}
else {
    setup_venv 'local'
    activate
}
