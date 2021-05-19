# Activate the CS Tools virtual environment.
#
# Written by: Nick Cooper <nicholas.cooper@thoughtspot.com>
# Last Modified: 2021/05/18
# Version: 0.1.0
#
# CHANGELOG
# v0.1.0 - INITIAL RELEASE
#
$NL = [Environment]::NewLine
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
    mkdir $APP_DIR -ErrorAction SilentlyContinue
    python -m venv "$APP_DIR\.cs_tools"
    & "$_ACTIVATE.ps1"

    if ( $install_type -eq 'local' ) {
        pip install -r reqs/offline-install.txt --find-links=pkgs/ --no-cache-dir --no-index
    }
    elseif ( $install_type -eq 'remote' ) {
        pip install -r reqs/requirements.txt --no-cache-dir --no-index   
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
        Start-Process cmd "/k $_ACTIVATE.bat && cs_tools"
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
