---
hide:
  - title
  - navigation
---

# Getting Started { hidden="" }

## What is __CS Tools__?

__CS Tools__ is a suite of tools written in :simple-python: __Python__ which connects to your __ThoughtSpot__ cluster through the [__V2.0 REST APIs__][ts-rest-apis].

They are designed to complement __ThoughtSpot__ native functionality with advanced automation and management capabilities.

!!! info "Important"

    While **CS Tools** is maintained by members of the __ThoughtSpot__ team, they are __TOTALLY FREE__!

    :exclamation: __ThoughtSpot [Support Team](https://community.thoughtspot.com)__ will be <span class=fc-red>unable to help</span> you resolve any issues.

    Instead, :bulb: __Feature Requests__{ .fc-purple } and :ring_buoy: __Support__{ .fc-green } are handled __{>__{ .fc-green} [__on Github Discussions__](https://github.com/thoughtspot/cs_tools/discussions) __<}__{ .fc-green }

~cs~tools tools --help

## Install

Follow the steps below to get __CS Tools__ installed on your platform.

<sub>*__CS Tools__* *requires at least python 3.9 to install!*{ .fc-purple }</>

=== ":fontawesome-brands-windows: &nbsp; Windows"

    Open up __Windows Terminal__ or __Powershell__.
    
    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```powershell
    powershell -ExecutionPolicy ByPass -c "IRM https://thoughtspot.github.io/cs_tools/install.py | python - --reinstall"
    ```

    <sup>_* changing the [execution policy][win-exec-pol] allows running a script from the internet_</>{ .fc-gray }

    !!! example "To open Powershell"
        Press the &nbsp; ++windows++ &nbsp; key, type __Powershell__{ .fc-purple }, then hit &nbsp; ++enter++

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: &nbsp; Mac, Linux"

    Open up a new __Terminal__ window.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    curl -LsSf https://thoughtspot.github.io/cs_tools/install.py | python - --reinstall
    ```

    ??? failure "command not found: python3"

        If you see this error in your terminal, try using `python` instead of `python3` above.

=== ":material-application-braces-outline: &nbsp; ThoughtSpot cluster"

    !!! danger "Proceed with caution! :dragon_face:"
        __CS Tools can run__ __pretty much anywhere__{ .fc-purple }__!__ We __strongly__ __recommend against__{ .fc-red }
        running this on your production __ThoughtSpot__ software cluster.

    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```bash
    curl -LsSf https://thoughtspot.github.io/cs_tools/install.py | python - --reinstall
    ```

    ??? failure "command not found: python3"

        If you see this error in your terminal, try using `python` instead of `python3` above.

=== ":simple-serverless: &nbsp; Serverless"

    If you want to run __CS Tools__ from a serverless environment, skip the install script and instead install the
    python package directly.

    === ":simple-github: &nbsp; GitHub Actions"

        ??? abstract "actions-workflow.yaml"

            ```yaml
            name: Extract Metadata with CS Tools.
            
            on:
              workflow_dispatch:
                inputs:
                  cs_tools_version:
                    description: "The CS Tools version to target for a manual run."
                    required: false
                    type: string
            
              schedule:
                # Runs every day at 5:20 AM UTC
                - cron: "20 5 * * *"
            
            jobs:
              extract_data_from_thoughtspot:
                runs-on: ubuntu-latest
            
                env:
                  # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
                  # https://thoughtspot.github.io/cs_tools/
                  CS_TOOLS_VERSION: ${{ github.event_name == 'workflow_dispatch' && inputs.cs_tools_version || 'v1.6.0' }}
                  CS_TOOLS_THOUGHTSPOT__URL: ${{ secrets.THOUGHTSPOT_URL }}
                  CS_TOOLS_THOUGHTSPOT__USERNAME: ${{ secrets.THOUGHTSPOT_USERNAME }}
                  CS_TOOLS_THOUGHTSPOT__SECRET_KEY: ${{ secrets.THOUGHTSPOT_SECRET_KEY }}
            
                  # COMMON PARAMETERS FOR THE SNOWFLAKE SYNCER
                  # https://thoughtspot.github.io/cs_tools/syncer/snowflake/
                  DECLARATIVE_SYNCER_SYNTAX:
                    "\
                    account_name=${{ secrets.SNOWFLAKE_ACCOUNT }}\
                    &username=${{ secrets.SNOWFLAKE_USERNAME }}\
                    &secret=${{ secrets.SNOWFLAKE_PASSWORD }}\
                    &warehouse=${{ secrets.SNOWFLAKE_WAREHOUSE }}\
                    &role=${{ secrets.SNOWFLAKE_ROLE }}\
                    &database=${{ secrets.SNOWFLAKE_DATABASE }}\
                    &schema=${{ secrets.SNOWFLAKE_SCHEMA }}\
                    &authentication=basic\
                    "
                
                steps:
                  # SETUP PYTHON.
                  - name: Set up Python
                    uses: actions/setup-python@v5
                  
                  # UPDATE PIP.
                  - name: Ensure pip is up to date.
                    run: python -m pip install --upgrade pip
            
                  # INSTALL A SPECIFIC VERSION OF cs_tools.
                  - name: Install a pinned version of CS Tools
                    run: python -m pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/${{ env.CS_TOOLS_VERSION }}.zip"
            
                  # ENSURE SYNCER DEPENDENCIES ARE INSTALLED.
                  #   found in: https://github.com/thoughtspot/cs_tools/blob/master/sync/<dialect>/MANIFEST.json
                  - name: Install a pinned version of CS Tools
                    run: python -m pip install "snowflake-sqlalchemy >= 1.6.1"
            
                  # RUNS THE searchable metadata COMMAND.
                  # https://thoughtspot.github.io/cs_tools/tools/searchable
                  #
                  # THE CLI OPTION  --config ENV:  TELLS CS TOOLS TO PULL THE INFORMATION FROM ENVIRONMENT VARIABLES.
                  - name: Refresh Metadata from ThoughtSpot
                    run: |
                      cs_tools tools
                      searchable metadata
                      --syncer 'snowflake://${{ env.DECLARATIVE_SYNCER_SYNTAX }}&load_strategy=TRUNCATE'
                      --config ENV:
            ```

    === ":simple-gitlab: &nbsp; GitLab CI/CD Pipelines"

        ??? abstract ".gitlab-ci.yml"

            ```yaml
            variables:
              # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
              # https://thoughtspot.github.io/cs_tools/
              CS_TOOLS_VERSION: "v1.6.0"
              CS_TOOLS_THOUGHTSPOT__URL: ${THOUGHTSPOT_URL}
              CS_TOOLS_THOUGHTSPOT__USERNAME: ${THOUGHTSPOT_USERNAME}
              CS_TOOLS_THOUGHTSPOT__SECRET_KEY: ${THOUGHTSPOT_SECRET_KEY}
  
              # COMMON PARAMETERS FOR THE SNOWFLAKE SYNCER
              # https://thoughtspot.github.io/cs_tools/syncer/snowflake/
              DECLARATIVE_SYNCER_SYNTAX:
                "\
                account_name=${SNOWFLAKE_ACCOUNT}\
                &username=${SNOWFLAKE_USERNAME}\
                &secret=${SNOWFLAKE_PASSWORD}\
                &warehouse=${SNOWFLAKE_WAREHOUSE}\
                &role=${SNOWFLAKE_ROLE}\
                &database=${SNOWFLAKE_DATABASE}\
                &schema=${SNOWFLAKE_SCHEMA}\
                &authentication=basic\
                "
  
            # WORKFLOW CAN BE TRIGGERED MANUALLY OR BY SCHEDULE
            workflow:
              rules:
                - if: $CI_PIPELINE_SOURCE == "schedule"
                - if: $CI_PIPELINE_SOURCE == "web"
  
            extract_data_from_thoughtspot:
              image: python:3.12-slim
              script:
                # UPDATE PIP.
                - python -m pip install --upgrade pip
  
                # INSTALL A SPECIFIC VERSION OF cs_tools.
                - python -m pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/${CS_TOOLS_VERSION}.zip"
  
                # ENSURE SYNCER DEPENDENCIES ARE INSTALLED.
                #   found in: https://github.com/thoughtspot/cs_tools/blob/master/sync/<dialect>/MANIFEST.json
                - python -m pip install "snowflake-sqlalchemy >= 1.6.1"
  
                # RUNS THE searchable metadata COMMAND.
                # https://thoughtspot.github.io/cs_tools/tools/searchable
                #
                # THE CLI OPTION  --config ENV:  TELLS CS TOOLS TO PULL THE INFORMATION FROM ENVIRONMENT VARIABLES.
                - >-
                cs_tools tools
                searchable metadata
                --syncer "snowflake://${DECLARATIVE_SYNCER_SYNTAX}&load_strategy=UPSERT"
                --config ENV:
  
            # RUNS EVERY DAY AT 5:20 AM UTC
            .schedule:
              cron: "20 5 * * *"
            ```

    === ":material-microsoft-azure-devops: &nbsp; Azure Pipelines"

        ??? abstract "azure-pipelines.yml"

            ```yaml
            variables:

              # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
              # https://thoughtspot.github.io/cs_tools/
              CS_TOOLS_VERSION: 'v1.6.0'
              CS_TOOLS_THOUGHTSPOT__URL: $(THOUGHTSPOT_URL)
              CS_TOOLS_THOUGHTSPOT__USERNAME: $(THOUGHTSPOT_USERNAME)
              CS_TOOLS_THOUGHTSPOT__SECRET_KEY: $(THOUGHTSPOT_SECRET_KEY)

              # NEEDED TO TELL CS TOOLS ABOUT THE ENVIRONMENT (Azure doesn't set this by default~)
              CI: true

              # COMMON PARAMETERS FOR THE SNOWFLAKE SYNCER
              # https://thoughtspot.github.io/cs_tools/syncer/snowflake/
              DECLARATIVE_SYNCER_SYNTAX: >-
                account_name=$(SNOWFLAKE_ACCOUNT)
                &username=$(SNOWFLAKE_USERNAME)
                &secret=$(SNOWFLAKE_PASSWORD)
                &warehouse=$(SNOWFLAKE_WAREHOUSE)
                &role=$(SNOWFLAKE_ROLE)
                &database=$(SNOWFLAKE_DATABASE)
                &schema=$(SNOWFLAKE_SCHEMA)
                &authentication=basic

            schedules:
            # Runs every day at 5:20 AM UTC
            - cron: '20 5 * * *'
              displayName: Daily metadata sync
              branches:
                include:
                - main
              always: true

            # DEFINE MANUAL TRIGGER CAPABILITY
            trigger: none # DISABLE CONTINUOUS INTEGRATION TRIGGER
            pr: none      # DISABLE PULL REQUEST TRIGGER

            # ALLOW MANUAL TRIGGER FROM AZURE DEVOPS UI
            resources:
              repositories:
              - repository: self

            pool:
              vmImage: 'ubuntu-latest'

            jobs:
            - job: extract_data_from_thoughtspot
              displayName: 'Extract Data from ThoughtSpot'
              steps:
              - task: UsePythonVersion@0
                inputs:
                  versionSpec: '3.12'
                  addToPath: true

              - script: |
                  # UPDATE PIP
                  python -m pip install --upgrade pip

                  # INSTALL A SPECIFIC VERSION OF cs_tools
                  python -m pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/$(CS_TOOLS_VERSION).zip"

                  # ENSURE SYNCER DEPENDENCIES ARE INSTALLED
                  python -m pip install "snowflake-sqlalchemy >= 1.6.1"

                  # RUNS THE searchable metadata COMMAND.
                  # https://thoughtspot.github.io/cs_tools/tools/searchable
                  #
                  # THE CLI OPTION  --config ENV:  TELLS CS TOOLS TO PULL THE INFORMATION FROM ENVIRONMENT VARIABLES.
                  cs_tools tools searchable metadata --syncer "snowflake://$(DECLARATIVE_SYNCER_SYNTAX)&load_strategy=UPSERT" --config ENV:
                displayName: 'Extract Metadata with CS Tools.'
            ```

    === ":simple-docker: &nbsp; Docker"

        ??? abstract "Dockerfile"

            ```shell
            # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
            # https://thoughtspot.github.io/cs_tools/
            docker build --build-arg CS_TOOLS_VERSION=v1.6.0 -t cs-tools-image:1.0.0 .
            ```

            ```shell
            # COMMON PARAMETERS FOR THE SNOWFLAKE SYNCER
            # https://thoughtspot.github.io/cs_tools/syncer/snowflake/
            docker run `
              -e CS_TOOLS_THOUGHTSPOT__URL="" `
              -e CS_TOOLS_THOUGHTSPOT_USERNAME="" `
              -e CS_TOOLS_THOUGHTSPOT_SECRET_KEY="" `
              -e DECLARATIVE_SYNCER_SYNTAX="" `
              cs-tools-image:1.0.0
            ```

            ```dockerfile
            # BASE DISTRIBUTION MUST INCLUDE PYTHON + PIP.
            FROM python:3.12-slim
            
            # METADATA
            LABEL version="1.0.0"
            LABEL description="ThoughtSpot CS Tools container"
            LABEL maintainer="https://github.com/thoughtspot/cs_tools/discussions"
            
            # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
            # https://thoughtspot.github.io/cs_tools/
            ARG CS_TOOLS_VERSION="v1.6.0"
            ENV CS_TOOLS_VERSION=${CS_TOOLS_VERSION}
            
            # AVOID PROMPTS FROM APT
            ENV DEBIAN_FRONTEND=noninteractive
            
            # INSTALL GIT (NEEDED FOR PIP INSTALL FROM GITHUB)
            RUN apt-get update && apt-get install -y \
                git \
                && apt-get clean \
                && rm -rf /var/lib/apt/lists/*
            
            # UPDATE PIP.
            RUN python3 -m pip install --upgrade pip
            
            # INSTALL A SPECIFIC VERSION OF cs_tools.
            RUN python3 -m pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/${CS_TOOLS_VERSION}.zip"
            
            # SET THE WORKING DIRECTORY
            WORKDIR /app
            
            # RUNS THE searchable metadata COMMAND.
            # https://thoughtspot.github.io/cs_tools/tools/searchable
            #
            # THE CLI OPTION  --config ENV:  TELLS CS TOOLS TO PULL THE INFORMATION FROM ENVIRONMENT VARIABLES.
            CMD ["sh", "-c", "cs_tools tools searchable metadata --syncer \"snowflake://${DECLARATIVE_SYNCER_SYNTAX}&load_strategy=UPSERT\" --config ENV:"]
            ```

    === ":simple-jupyter: &nbsp; Python Notebook"

        ??? abstract "Untitled.ipynb"

            ```markdown
            ### Install CS Tools

            Change the `v1.6.0` for any version or branch you want, but the latest version has all the bells as whistles.
            ```

            ```python
            !pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/v1.6.0.zip"
            ```

            ```python
            from cs_tools.programmatic import CSToolInfo
            import os
            ```

            ```markdown
            ### While [CS Tools](https://thoughtspot.github.io/cs_tools/) is a CLI, we can still use it programmatically.

            The simplest way to specify your config is to set environment variables.
            ```

            ```python
            os.environ["CS_TOOLS_THOUGHTSPOT__URL"] = ...
            os.environ["CS_TOOLS_THOUGHTSPOT__USERNAME"] = ...
            os.environ["CS_TOOLS_THOUGHTSPOT__SECRET_KEY"] = ...
            # os.environ["CS_TOOLS_THOUGHTSPOT__PASSWORD"] = ...
            # os.environ["CS_TOOLS_THOUGHTSPOT__TOKEN"] = ...
            ```

            ```markdown
            ### Common Parameters for the [Snowflake Syncer](https://thoughtspot.github.io/cs_tools/syncer/snowflake/)

            __Load Strategies__
            - `UPSERT` _update or insert incoming rows_
            - `TRUNCATE` _first delete all rows, then insert incoming rows_
            - `APPEND` _only insert, without regarding primary key_
            ```

            ```python
            UPSERT_SYNCER_CONF = {
                "account_name": ...,
                "username": ...,
                "secret": ...,
                "warehouse": ...,
                "role": ...,
                "database": ...,
                "schema": ...,
                "authentication": "basic",
                "load_strategy": "UPSERT",
            }

            syncer_def = "&".join(f"{k}={v}" for k, v in UPSERT_SYNCER_CONF.items())
            ```

            ```markdown
            ### Runs the [`searchable metadata` command](https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#metadata_1)

            The option `--config ENV:` tells CS Tools to fetch config information from the environment variables we set earlier.
            ```

            ```python
            searchable = CSToolInfo.fetch_builtin(name="searchable")
            searchable.invoke("metadata", "--syncer", f"snowflake://{syncer_def}", "--config", "ENV:")
            ```

---

## Configure

In order to use the APIs, __ThoughtSpot__ enforces [__authenticated sessions__][ts-sess-auth]. All of the standard
__ThoughtSpot__ security controls apply.

!!! info "CS Tools offers support for.."

    === ":material-form-textbox-password: &nbsp; Basic Auth"
        This is your standard combination of __username__{ .fc-purple } and __password__{ .fc-purple }.

        - [__Basic Authentication__][ts-rest-auth-basic]

        :rotating_light: Your password is not held in cleartext.

    === ":material-handshake: &nbsp; Trusted Auth"
        This is a global password which allows you to log in as any user you choose. You can find the __Secret
        Key__{ .fc-purple } in the __Developer tab__ under __Security Settings__.

        - [__Trusted Authentication__][ts-rest-auth-trusted]

        :superhero: Only Administrators can see the Trusted Authentication secret key.

    === ":material-teddy-bear: &nbsp; Bearer Token"
        This is a user-local password placement with a designated lifetime. Call the API with your password (or secret
        key) to receieve a __bearer token__{ .fc-purple }.

        - [__Bearer Token Authentication__][ts-rest-auth-bearer-token]

        :clock11: This token will expire after the `validitiy_time_in_sec`.

Type the command `cs_tools config create --help` and press &nbsp; ++enter++ .

~cs~tools config create --help
<sup class="fc-gray"><i>any option marked with a red asterisk ( __*__{ .fc-red } ) is __required__{ .fc-red }.</i></sup>

`cs_tools config create --config dogfood --url https://anonymous.thoughtspot.cloud --username anonymous`

??? success "Successful config output"

    ~cs~tools config check --anonymous --config ENV:


[cs-tools-discussions]: https://github.com/thoughtspot/cs_tools/discussions
[ts-rest-apis]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-sess-auth]: https://developers.thoughtspot.com/docs/api-authv2
[ts-rest-auth-basic]: https://developers.thoughtspot.com/docs/api-authv2#_basic_authentication
[ts-rest-auth-trusted]: https://developers.thoughtspot.com/docs/api-authv2#trusted-auth-v2
[ts-rest-auth-bearer-token]: https://developers.thoughtspot.com/docs/api-authv2#bearerToken
[win-exec-pol]: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.4#powershell-execution-policies
[get-rust]: https://www.rust-lang.org/tools/install