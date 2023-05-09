# Installing & Upgrading the Tools

__CS Tools__ is a command line utility written in :fontawesome-brands-python: __Python__ which connects to your
__ThoughtSpot__ cluster through the [REST APIs][ts-rest-apis].

??? warning "Don't have Python installed yet?"

    __Python 3.7 or greater is__ __required__{ .fc-red } __to install CS Tools!__

    === ":fontawesome-brands-windows: Windows"
        If you've never worked directly with __Python__ before, chances are it is not installed on your computer.

        In __PowerShell__{ .fc-blue }, try typing `python --version`. In order for __CS Tools__ to run appropriately,
        this version must be greater than the __requirement__{ .fc-red } above.

        If you do not have python installed, or your version is not greater than the above version, you can install it
        by going to Python's [downloads website][python].

        :rotating_light: __Make sure you check__{ .fc-purple } __Customize Installation__{ .fc-orange } __and__{ .fc-purple } __add Python
        to your__{ .fc-orange } `PATH`. :rotating_light:

    === ":fontawesome-brands-apple: Mac"
        More than likely, you have multiple versions of Python bundled with your distribution.

        In __Terminal__, try typing `python --version`.

        If it comes back with something like `Python 2.7.18`, try again with `python3 --version`. In order for
        __CS Tools__ to run appropriately, this version must be greater than the __requirement__{ .fc-red } above.

        If your version of python is not greater than the above version, you can install it by going to Python's
        [downloads website][python].

    === ":fontawesome-brands-linux: Linux"
        More than likely, you have multiple versions of Python bundled with your distribution.

        Try typing `python --version`.

        If it comes back with something like `Python 2.7.18`, try again with `python3 --version`. In order for
        __CS Tools__ to run appropriately, this version must be greater than the __requirement__{ .fc-red } above.

        ---

        __Before upgrading__{ .fc-red }, __you should consult with your system administration team__ to understand if
        it's acceptable to install multiple versions on this hardware.

        One alternative for installing multiple system-level python distributions is [`pyenv`][pyenv].

    === ":material-application-braces-outline: ThoughtSpot cluster"
        More than likely, you are good to go! Python is installed with every cluster configuration.

        __If you are on__{ .fc-red } __ThoughtSpot-managed CentOS__{ .fc-black } __and installed__{ .fc-red }
        __ThoughtSpot__{ .fc-black } __prior to Software version 8.4.1__{ .fc-red }, <br/>then you may need to upgrade
        your system python version.

        __ThoughtSpot__ provides instructions on [how to do this][ts-upgrade-python]. 

        __This incurs downtime event.__{ .fc-red }

---

## First Time Install

The __CS Tools__ bootstrapper will install or upgrade your isolated __CS Tools__ environment. After the first install,
you will be able to run upgrades from directly within the __CS Tools__ application.

??? question "Don't have access to the outside internet?"

    __You still have options!__{ .fc-green } We offer an offline binary to install, but require a bit of information first. 

    Run the following python command to gather your environment information -- we'll need the first few lines.

    ```shell
    python -m sysconfig
    ```

    Reach out to the [__CS Tools team on Discussions__][gh-discussions] with this information so we can help you get started.

!!! tip inline end "Your platform"

    ### :fontawesome-brands-windows: Windows

    The new [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-gb&gl=GB) runs __CS Tools__ beautifully.

    ### :fontawesome-brands-apple: Mac OS

    The default terminal app is limited to 256 colors. We recommend installing a newer terminal such as [iterm2](https://iterm2.com/), [Kitty](https://sw.kovidgoyal.net/kitty/), or [WezTerm](https://wezfurlong.org/wezterm/).

    ### :fontawesome-brands-linux: Linux (all distros)

    All Linux distros come with a terminal emulator that can run __CS Tools__.

Follow the steps below to get __CS Tools__ installed on your platform.

=== ":fontawesome-brands-windows: Windows"

    Open up __Windows Terminal__ or __Powershell__.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```powershell
    (Invoke-WebRequest `# (1)!
        -Uri https://raw.githubusercontent.com/thoughtspot/cs_tools/master/cs_tools/updater/_bootstrapper.py `
        -UseBasicParsing `
    ).Content | python - --install # (2)!
    ```

    1.  `Invoke-WebRequest` is like `curl`, but for Windows. It will download a file from the URL specified.
    2.  The `IWR` response is sent or "piped" to `python` for install.

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: Mac, Linux"

    Open up a new __Terminal__ window.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    curl \
        --silent --show-error --location-trusted \
        https://raw.githubusercontent.com/thoughtspot/cs_tools/master/cs_tools/updater/_bootstrapper.py \
        | python3 - --install # (2)!
    ```

    1.  These are the longhand form of the `-sSL` flags.
    2.  The `curl` response is sent or "piped" to `python` for install.

    ??? failure "command not found: python3"

        If you see this error in your terminal, try using `python` instead of `python3` above.

=== ":material-application-braces-outline: ThoughtSpot cluster"
    
    __We strongly recommend against this option.__{ .fc-red } Your __ThoughtSpot__ cluster is a production system
    serving your entire user community. While __CS Tools__ is not a resource-hungry application and only runs for short
    periods of time, it should ideally be run from another machine.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    curl \
        --silent --show-error --location-trusted \
        https://raw.githubusercontent.com/thoughtspot/cs_tools/master/cs_tools/updater/_bootstrapper.py \
        | python3 - --install # (2)!
    ```

    1.  These are the longhand form of the `-sSL` flags.
    2.  The `curl` response is sent or "piped" to `python` for install.

    ??? failure "command not found: python3"

        If you see this error in your terminal, try using `python` instead of `python3` above.


??? tip "Upgrading from a recent version?"

    Try using __CS Tools__ itself!

    ~cs~tools cs_tools self upgrade --help


Try running __CS Tools__ by typing..

~cs~tools cs_tools self info --anonymous

!!! info "Where can I reach out for help?"

    __CS Tools__ is maintained by our __Solutions Consultants__ with contributions from you, our customers!

    ==__You <span class=fc-red>should not</span> raise a Support Case in order to get the proper help.__==

    :wave: <b class=fc-purple>Please join us on [Github Discussions][gh-discussions].</b>

---

## Configure CS Tools

__CS Tools__ supports being run against many different platforms. Configuration files represent a way to define a
specific user interacting with __ThoughtSpot__ programmatically.

This can be helpful if you maintain both a __Production__ and __Non-Production__ environment, or if you operate as a
center of excellence and want to provide your domain managers with programmatic access to the portion of
__ThoughtSpot__.

__Read on to the next section__ to learn about how to set up a configuration file.


[ts-rest-apis]: https://developers.thoughtspot.com/docs/?pageid=rest-apis
[ts-upgrade-python]: https://docs.thoughtspot.com/software/latest/python-upgrade#_upgrade_your_python_version
[gh-discussions]: https://github.com/thoughtspot/cs_tools/discussions
[pyenv]: https://github.com/pyenv/pyenv
[python]: https://www.python.org/downloads/
