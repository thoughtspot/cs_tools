---
hide:
  - navigation
---

# TML Deployments CI/CD

Initial development is fast and exciting in __ThoughtSpot__, but what happens when you need to ensure your new data
product is safe in the event of catastrophic failure? How can you continue new development without impacting your users
in __Production__{ .fc-green }?

This is where __TML__ comes into play. ThoughtSpot has<sup>[[1]][deploy-overview]</sup> many<sup>[[2]][deploy-git]</sup> 
guides<sup>[[3]][deploy-tml]</sup> on how to handle changes programmatically between environments, and they all
fundamentally rely on the same few principles.

- __Checkpointing__ your ThoughtSpot objects
- __Storing__ those objects in safe keeping
- __Deploying__ those objects to a new environment

??? tinm "There is No Magic!"

    Remember, __CS Tools__ wraps the __ThoughtSpot__ [__REST APIs__][ts-rest-v2]. This tool uses the following endpoints.

    - [`/metadata/search`][ts-rest-metadata-search] *for aggregating GUIDs from content you want to checkpoint*{ .fc-gray}
    - [`/metadata/tml/export`][ts-rest-metadata-tml-export] *for checkpointing TML*{ .fc-gray }
    - [`/metadata/tml/import`][ts-rest-metadata-tml-import] *for validating TML prior to importing it*{ .fc-gray }
    - [`/metadata/tml/import`][ts-rest-metadata-tml-import] *for deploying TML to a new environment*{ .fc-gray }
    - [`/tags/assign`][ts-rest-tags-assign] *for assigning one or more tags to deployed content*{ .fc-gray}

!!! tip ""

    === "--help"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools scriptability --help
            ```
        ~cs~tools tools scriptability --help
    === "checkpoint"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools scriptability checkpoint --help
            ```
        ~cs~tools tools scriptability checkpoint --help
    === "deploy"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools scriptability deploy --help
            ```
        ~cs~tools tools scriptability deploy --help

---

### Snapshot Your Objects

Snapshotting your objects is a lot like "saving your work" in other workflows. In __CS Tools__, we give you the option
to collect up many objects and create a `checkpoint` (sometimes called a `commit`).

__CS Tools__ doesn't actually save any state for you, but it will export your the TML of your objects in a consistent
format, and also store a `.mappings/<environment>.json` file alongside them.

!!! danger ""
    __This file is__ __critical to working with TML__{ .fc-red }__, and you should not edit it [unless you absolutely
    know what you're doing][deploy-guid-map]!__

The optional `--environment` parameter is a way for you to give a friendly name to your [__Environment__][deploy-overview-bp].
Remember this name though, as it will be used in order to appropriately deploy your objects!

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools scriptability checkpoint --help
        ```
    ~cs~tools tools scriptability checkpoint --help

---

### Deploy your Objects

Once you are ready to push your changes to a [__new environment__][deploy-overview-bp], you can use the `deploy`
command. This command provides you the ability to perform mutliple different styles of deployments.

The `--source-environment` and `--target-environment` parameters are __required__{ .fc-red} and should map to the same
names you consistently use to describe the place you've extracted TML and the place you want to deploy TML.

For example, if you have a `develop` Org and a `production` Org in __ThoughtSpot__, you may choose to call these
environments `develop` and `production` respectively. It would also be a good idea to have branches in `git` called
`ts-develop` and `ts-production` in order to signify to all users that these two branches map to the __ThoughtSpot__
environments with the same name.

??? tinm "OK, there's a little bit of Magic."
    __CS Tools__ maintains *multiple* mapping files. Every time you deploy to a new environment, __CS Tools__ will
    search for a mapping file with the `--source-environment` name, the `--target-environment` name, and then [merge the
    two files together][scriptability-merge] intelligently.

    This allows us to automatically map GUIDs to your new destination environment and avoid merge conflicts on the
    actual mapping itself.

=== "Selective Types"
    Provide a comma-separated list of types __without spaces__{ .fc-purple } to import into __ThoughtSpot__.

    It can be useful to batch together your types into multiple groups, for better import performance.

    - [x] `TABLE,SQL_VIEW` - the base layer of the object hierarchy in __ThoughtSpot__.
    - [x] `VIEW,MODEL` - the semantic model layer of the object hierarchy.
    - [x] `ANSWER,LIVEBOARD` - the user layer of the object hierarchy.

    !!! note ""
        __Connections__ will always fail to sucessfully import. This is because connections require authentication
        details, and __CS Tools__ does not provide a mechanism to automatically fill this in. It is __recommended__{ .fc-green }
        to use Connection APIs to update connections as opposed to deploying changed via TML.

=== "Deploy Type"
    __CS Tools__ takes a little bit of metadata on your `scriptability` actions and stores it in a history within your
    mapping file. This history is used not only for descriptive purposes, but also to understand if any new objects are
    available for deployment.

    This is an __optimization technique__{ .fc-green } that helps your __ThoughtSpot__ cluster avoid processing incoming
    TML files that are identical to those that already exist in the system. It is recommended to use `DELTA` mode when
    your deployments become more complex.

    - [x] `DELTA` - based on the last successful deployment, only attempt to deploy newly modified objects.
    - [x] `FULL` - regardless of prior deployments, treat all objects as newly modified.

=== "Deploy Policy"
    - [x] `VALIDATE_ONLY` - regardless of status, no TML will be imported, all status messages are printed on screen.
    - [x] `PARTIAL` - if any TML imports (any error code is __OK__{ .fc-green } or __WARNING__{ .fc-orange }), then the job succeeds.
    - [x] `ALL_OR_NONE` - if any TML fails to import FULLY (all error codes must be __OK__{ .fc-green }), then the entire job fails.

??? tip "Use Tags to your advantage"

    This command will assign any number of tags to deployed objects. __This can combo really well__{ .fc-green } with
    other commands who take their input from tags as well!

    === "bulk-sharing from-tag"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools bulk-sharing from-tag --help
            ```
        ~cs~tools tools bulk-sharing from-tag --help
    === "user-management transfer --tags"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools user-management transfer --help
            ```
        ~cs~tools tools user-management transfer --help
    === "bulk-deleter from-tag --tag-only"
        ??? abstract "Get the Command"
            ```shell
            cs_tools tools bulk-deleter from-tag --help
            ```
        ~cs~tools tools bulk-deleter from-tag --help

!!! tip ""
    ??? abstract "Get the Command"
        ```shell
        cs_tools tools scriptability deploy --help
        ```
    ~cs~tools tools scriptability deploy --help

---

### Where to Store

The most common place to store your objects is a version control system like [__Git__][what-is-git].

__We'll show some common ways to handle commiting your changes to the underlying git repository.__{ .fc-purple }

In the examples, we'll assume the following.

  - [x] A directory structure that looks like this, where we want to commit our changes to the `project-a` directory.
    ```
    root
    ├── .git
    ├── .gitignore
    ├── README.md
    │
    ├── /project-a
    │   ├── .mappings/
    │   ├── connection/
    │   ├── table/
    │   ├── model/
    │   └── liveboard/
    │   
    └── /project-b
        └── ...
    ```
  - [x] You have already ran `scriptability checkpoint` to extract files from __ThoughtSpot__ to the `project-a` directory.
  - [x] You are trying to take a snapshot of your [__Environment__][deploy-overview-bp] called __Develop__{ .fc-purple }.
  - [x] Your current working directory is at the root of your repository.

!!! warning "Important"
    It's important to note that both `scriptability checkpoint` and `scriptability deploy` will use produce files when
    run.
    
    __This means you MUST run__{ .fc-red } one of the below commit processes in order to capture those changes and
    complete the CI workflow!

=== ":simple-git: &nbsp; git (local)"
    ??? abstract "commit.sh"
        ```shell
        git switch ts-develop
        git add project-a/
        git commit -m "AUTOCOMMIT >> checkpoint files from ThoughtSpot"
        git push origin ts-develop
        ```
        <sup>*\*The above assumes you have already created the git repo with `git init`!*{ .fc-gray }</sup>

=== ":simple-github: &nbsp; GitHub"
    ??? abstract "actions-workflow.yaml"
        ```yaml
        jobs:
          commit_changes:
            runs-on: ubuntu-latest

            env:
              # USER-SPECIFIED VARIABLES
              DIRECTORY: "project-a"
              COMMIT_MESSAGE: "AUTOCOMMIT >> checkpoint files from ThoughtSpot"
              ENVIRONMENT_NAME: "ts-develop"  # or.. ${{ github.ref_name }}

            steps:
              # MAKE SURE WE'RE ON THE RIGHT BRANCH BEFORE ADDING FILES
              - name: Checkout code
                uses: actions/checkout@v4
                with:
                  ref: 
                  # FETCH ALL HISTORY TO ENSURE PROPER CHECKOUT
                  fetch-depth: 0
                  token: ${{ secrets.GITHUB_TOKEN }}
            
              # SETUP AUTOCOMMITER
              - name: Configure Git
                run: |
                  git config --global user.name "GitHub Actions"
                  git config --global user.email "github-actions@github.com"
            
              # MAKE SURE WE'RE ON THE RIGHT BRANCH BEFORE ADDING FILES
              # ADD ALL FILES IN THE DIRECTORY
              # CREATE COMMIT, SKIPPING RE-TRIGGERING CI.
              # PUSH CHANGES BACK USING THE ACCESS TOKEN
              - name: Commit and push changes
                run: |
                  git checkout ${{ env.ENVIRONMENT_NAME }}
                  git add ${{ env.DIRECTORY }}/
                  git commit -m "${{ env.COMMIT_MESSAGE }}" || echo "No changes to commit"
                  git push
                env:
                  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        ```
        <sup>*\*The only required variables above are `DIRECTORY`, `COMMIT_MESSAGE`, and `ENVIRONMENT_NAME`. All others are set from [Defaults][github-ci-vars]!*{ .fc-gray }</sup>

=== ":simple-gitlab: &nbsp; GitLab"
    ??? abstract ".gitlab-ci.yml"
        ```yaml
        commit_changes:
          stage: commit
          image: alpine:latest

          variables:
            # WE'LL USE FETCH STRATEGY TO PUSH CHANGES BACK TO GIT
            GIT_STRATEGY: fetch
            GIT_CHECKOUT: "true"
  
            # USER-SPECIFIED VARIABLES
            DIRECTORY: "project-a"
            COMMIT_MESSAGE: "AUTOCOMMIT >> checkpoint files from ThoughtSpot"
            ENVIRONMENT_NAME: "ts-develop"  # or.. ${CI_COMMIT_REF_NAME}

          script:
            # INSTALL GIT AND SETUP AUTOCOMMITER
            - apk add --no-cache git
            - git config --global user.name "GitLab CI"
            - git config --global user.email "gitlab-ci@nowhere.io"
    
            # MAKE SURE WE'RE ON THE RIGHT BRANCH BEFORE ADDING FILES
            - git checkout ${ENVIRONMENT_NAME}
    
            # ADD ALL FILES IN THE DIRECTORY
            - git add ${DIRECTORY}/
    
            # CREATE COMMIT, SKIPPING RE-TRIGGERING CI.
            - git commit -m "${COMMIT_MESSAGE} [skip ci]"
    
            # PUSH CHANGES BACK USING THE ACCESS TOKEN
            - git push "https://oauth2:${GITLAB_ACCESS_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git" HEAD:${ENVIRONMENT_NAME}
        ```
        <sup>*\*The only required variables above are `DIRECTORY`, `COMMIT_MESSAGE`, and `ENVIRONMENT_NAME`. All others are set from [Defaults][gitlab-ci-vars]!*{ .fc-gray }</sup>
    
    Since __CS Tools__ is handling the "fetch TML from ThoughtSpot" and "deploy TML back to ThoughtSpot" pieces of the
    deployment workflows, all we're left to do is solve the "How do I track my changes?" problem.

    While this is totally outside of the scope of __ThoughtSpot__, the above workflows should offer helpful guidance on
    the steps necessary to commit to a repository.

---

### Full Example Workflows

These workflows show the complete CI/CD pattern and can be used as a base for getting starting with your own process.
If you are familiar with your CI platform, these can be extended with __Pull / Merge Request templates__ for even
greater flexibility in managing __ThoughtSpot__ deployments.

=== ":simple-github: &nbsp; GitHub"
    ??? abstract "actions-workflow.yaml"
        __Coming soon!__{ .fc-purple}

=== ":simple-gitlab: &nbsp; GitLab"
    ??? abstract ".gitlab-ci.yml"
        ```yaml
        stages:
          - extract
          - validate
          - deploy
          - commit

        workflow:
          rules:
            - if: $CI_PIPELINE_SOURCE == "web"
            - if: $CI_PIPELINE_SOURCE == "schedule"

        .cs_tools_setup:
          variables:
            CS_TOOLS_VERSION: "v1.6.2"

          before_script:
            # ENSURE PIP IS UP TO DATE.
            - python -m pip install --upgrade pip

            # INSTALL A SPECIFIC VERSION OF cs_tools.
            - python -m pip install "cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/${CS_TOOLS_VERSION}.zip"

        variables:
          # DEFAULT PIPELINE TYPE WILL BE OVERRIDDEN BY WORKFLOW RULES
          PIPELINE_TYPE: "commit"

          # CS TOOLS IS COMMAND LINE LIBRARY WRAPPING TS APIS
          # THE CLI OPTION  --config ENV:  TELLS CS TOOLS TO PULL THE INFORMATION FROM ENVIRONMENT VARIABLES.
          CS_TOOLS_THOUGHTSPOT__URL: ${THOUGHTSPOT_URL}
          CS_TOOLS_THOUGHTSPOT__USERNAME: ${THOUGHTSPOT_USERNAME}
          CS_TOOLS_THOUGHTSPOT__SECRET_KEY: ${THOUGHTSPOT_SECRET_KEY}

          # GIT OPTIONS
          DIRECTORY: "dogfood"
          COMMIT_MESSAGE: "AUTOMATED >> TS-CI ${PIPELINE_TYPE} from ${CI_PIPELINE_SOURCE}"


        extract_tml_from_thoughtspot:
          stage: extract
          image: python:3.12-slim
          rules:
            - if: $PIPELINE_TYPE == "commit"

          variables:
            CS_TOOLS_VERSION: !reference [.cs_tools_setup, variables, CS_TOOLS_VERSION]
            TS_METADATA_TYPES: "ALL"
            TS_OBJECT_TAG: "CS Tools"
            TS_ORG: "Primary"
            TS_SOURCE_ENV_NAME: "champagne_primary"
          
          before_script:
            - !reference [.cs_tools_setup, before_script]

          script:
            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#scriptability
            - cs_tools tools scriptability checkpoint --directory ${DIRECTORY} --environment ${TS_SOURCE_ENV_NAME} --metadata-types ${TS_METADATA_TYPES} --tags "${TS_OBJECT_TAG}" --org "${TS_ORG}" --config "ENV:"

          artifacts:
            paths:
              - ${DIRECTORY}/

        validate_tml_on_thoughtspot:
          stage: validate
          image: python:3.12-slim
          rules:
            - if: $PIPELINE_TYPE == "validate"
          
          before_script:
            - !reference [.cs_tools_setup, before_script]

          variables:
            CS_TOOLS_VERSION: !reference [.cs_tools_setup, variables, CS_TOOLS_VERSION]
            TS_METADATA_TYPES: "TABLE"
            TS_ORG: "temp-dev"
            TS_SOURCE_ENV_NAME: "champagne_primary"
            TS_TARGET_ENV_NAME: "temp-dev"
            TS_DEPLOY_TYPE: "DELTA"

          script:
            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#scriptability
            - cs_tools tools scriptability deploy --directory ${DIRECTORY} --source-environment ${TS_SOURCE_ENV_NAME} --target-environment ${TS_TARGET_ENV_NAME} --deploy-type ${TS_DEPLOY_TYPE} --deploy-policy VALIDATE_ONLY --metadata-types ${TS_METADATA_TYPES} --org "${TS_ORG}" --config "ENV:"

        deploy_tml_to_thoughtspot:
          stage: deploy
          image: python:3.12-slim
          rules:
            - if: $PIPELINE_TYPE == "deploy"

          before_script:
            - !reference [.cs_tools_setup, before_script]

          variables:
            CS_TOOLS_VERSION: !reference [.cs_tools_setup, variables, CS_TOOLS_VERSION]
            TS_ORG: "temp-dev"
            TS_METADATA_TYPES: "TABLE"
            TS_OBJECT_TAG: "temporary-tag-for-ci"
            TS_SOURCE_ENV_NAME: "champagne_primary"
            TS_TARGET_ENV_NAME: "temp-dev"
            TS_DEPLOY_TYPE: "DELTA"
            TS_DEPLOY_POLICY: "ALL_OR_NONE"
            TS_CONTENT_AUTHOR: ""
            TS_SHARE_TO_GROUP: ""
            TS_SHARE_MODE: "READ_ONLY"

          script:
            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#deploy_2
            - cs_tools tools scriptability deploy --directory ${DIRECTORY} --source-environment ${TS_SOURCE_ENV_NAME} --target-environment ${TS_TARGET_ENV_NAME} --deploy-type ${TS_DEPLOY_TYPE} --deploy-policy ${TS_DEPLOY_POLICY} --metadata-types ${TS_METADATA_TYPES} --tags "${TS_OBJECT_TAG}" --org "${TS_ORG}" --config "ENV:"

            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#transfer
            - |
              if [ -n "${TS_CONTENT_AUTHOR}" ]; then
                cs_tools tools user-management transfer --tags ${TS_OBJECT_TAG} --to ${TS_CONTENT_AUTHOR} --org "${TS_ORG}" --config "ENV:"
              else
                echo "Skipping ASSIGN_CONTENT_AUTHOR as $TS_CONTENT_AUTHOR is empty."
              fi

            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#from-tag_1
            - |
              if [ -n "${TS_SHARE_TO_GROUP}" ]; then
                cs_tools tools bulk-sharing from-tag --tag ${TS_OBJECT_TAG} --groups "${TS_SHARE_TO_GROUP}" --share-mode ${TS_SHARE_MODE} --no-prompt --org "${TS_ORG}" --config "ENV:"
              else
                echo "Skipping SHARING_CONTENT as $TS_SHARE_TO_GROUP is empty."
              fi

            # https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#from-tag
            - cs_tools tools bulk-deleter from-tag --tag ${TS_OBJECT_TAG} --tag-only --no-prompt --org "${TS_ORG}" --config "ENV:"

          artifacts:
            paths:
              - ${DIRECTORY}/

        commit_changes:
          stage: commit
          image: alpine:latest
          rules:
            - if: $PIPELINE_TYPE != "validate"
          needs:
            - job: extract_tml_from_thoughtspot
              artifacts: true
              optional: true
            - job: deploy_tml_to_thoughtspot
              artifacts: true
              optional: true

          variables:
            # WE'LL USE FETCH STRATEGY TO PUSH CHANGES BACK TO GIT
            GIT_STRATEGY: fetch
            GIT_CHECKOUT: "true"

          script:
            # INSTALL GIT AND SETUP AUTOCOMMITER
            - apk add --no-cache git
            - git config --global user.name "GitLab CI"
            - git config --global user.email "gitlab-ci@nowhere.io"

            # MAKE SURE WE'RE ON THE RIGHT BRANCH BEFORE ADDING FILES
            - git checkout ${CI_COMMIT_REF_NAME}

            # ADD ALL FILES IN THE DIRECTORY
            - git add ${DIRECTORY}/

            # CREATE COMMIT, SKIPPING RE-TRIGGERING CI.
            - git commit -m "${COMMIT_MESSAGE} [skip ci]"

            # PUSH CHANGES BACK USING THE ACCESS TOKEN
            - git push "https://oauth2:${GITLAB_ACCESS_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git" HEAD:${CI_COMMIT_REF_NAME}
        ```

=== ":simple-docker: &nbsp; Docker"
    ??? abstract "Dockerfile"
        __Coming soon!__{ .fc-purple}


---

### Frequently Asked Questions

??? question "Can CS Tools deploy TML if I would break my downstream dependents in Production?"
    __No.__{ .fc-red } __CS Tools__ simply runs the `tml/import` API after mapping the target environment's GUIDs onto
    the incoming TML. However, it cannot change the limitations that the target __ThoughtSpot__ system imposes.

    There are ways to mitigate breaking changes in __ThoughtSpot__ and avoid the dependency problem, but they are out of
    scope for this guide.

??? question "Will CS Tools manage my merge conflicts?"
    __No.__{ .fc-red } Simply put, __CS Tools__ as a codebase has no idea `git` even exists. This is done intentionally,
    as it leaves `git` itself to handle, warn, or block on any specific issues related to the version controlling system.

    There are ways to effectively handle merge conflicts in `git`, but they are out of scope for this guide.

??? question "What happens if I don't push my changes to a repository?"
    Typically -- it is a non-destructive action to export or import TML. If you were testing your workflow and forgot to
    commit the last round of changes to your branch, you can typically re-run the workflow and either checkpoint or
    deploy again. <span class=fc-green>Just make sure to save your work the second time!</span>

??? question "Can I revert a commit?"
    __Yes!__ This is a function of `git` itself and can be thought of as "totally outside the scope of __CS Tools__".
    However, if you are trying to __deploy__{ .fc-purple } a prior commit back up to you __ThoughtSpot__ environment,
    then the question really becomes <span class=fc-green>"Can CS Tools deploy TML if I would break my downstream
    dependents in Production?"</span>

---

[what-is-git]: https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F
[deploy-overview]: https://developers.thoughtspot.com/docs/development-and-deployment
[deploy-overview-bp]: https://developers.thoughtspot.com/docs/development-and-deployment#_best_practices
[deploy-guid-map]: https://developers.thoughtspot.com/docs/deploy-with-tml-apis#guidMapping
[deploy-git]: https://developers.thoughtspot.com/docs/git-integration
[deploy-tml]: https://developers.thoughtspot.com/docs/deploy-with-tml-apis
[scriptability-merge]: https://github.com/thoughtspot/cs_tools/blob/ec907ae1e2cbabb9415590f6f8b7bbd5f0e318ea/cs_tools/cli/tools/scriptability/utils.py#L117-L169
[github-ci-vars]: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
[gitlab-ci-vars]: https://docs.gitlab.com/ci/variables/predefined_variables/
[ts-rest-v2]: https://developers.thoughtspot.com/docs/rest-apiv2-reference
[ts-rest-metadata-search]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fsearch-metadata
[ts-rest-tags-assign]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Ftags%2Fassign-tag
[ts-rest-metadata-tml-import]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fimport-metadata-tml
[ts-rest-metadata-tml-export]: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fmetadata%2Fexport-metadata-tml
