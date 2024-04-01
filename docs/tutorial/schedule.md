---
hide:
    - toc
    - footer
---

# Scheduling with __CS Tools__

__Archiver__{ .fc-purple } is a powerful tool in your arsenal as a __ThoughtSpot__ administrator and in order to take
full advantage of it, you'll want to schedule it to run regularly.

It can be helpful to keep close tabs on the amount of stale content that exists in your platform. Let's schedule our
__Archiver__{ .fc-purple } identification report to export from the platform once every week.

!!! tip "CS Tools"

    Since __CS Tools__ lives on your `PATH`, even though the code exists in an isolated environment, the entrypoint can
    be reached anywhere on your system.


## Schedule it

Now that we've decided how to track our content, we're ready to schedule our command to run weekly.

=== ":fontawesome-brands-windows: Task Scheduler"

    Find the Task Scheduler in your system utilities.

    === "Create a New Task."
        ![windows-task](../assets/images/windows-schedule-task.png)

    === "Weekly Recurring Trigger."
        ![windows-trigger](../assets/images/windows-schedule-trigger.png)

    === "Targeting `cs_tools`."
        ![windows-target](../assets/images/windows-schedule-target.png)

=== ":fontawesome-brands-apple: :fontawesome-brands-linux: :fontawesome-brands-centos: crontab"

    !!! hint "Need help?"

        [https://crontab.guru][cronguru]

        *A helpful online utility for writing your cron schedule expressions.*
    
    <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
    ```cron
    # Weekly, on Monday at 3:05am
     5  3  *  *  1  cs_tools tools archiver identify --syncer csv://directory=$HOME/Downloads --config non-prod
    ```

=== ":simple-serverless: Serverless"

    __Here are some examples.__{ .fc-green } It's still recommended to test __CS Tools__ locally first.

    === ":simple-githubactions: GitHub Actions"
        `actions-workflow.yaml`
        ```yaml
        name:
          Extract data with CS Tools.

        on:
          schedule:
            # Runs every day at 3:15 AM UTC
            - cron: "15 3 * * *"

        jobs:
          extract_data_from_thoughtspot:

            # Configure Environment Variables for CS Tools configuration
            env:
              CS_TOOLS_THOUGHTSPOT__URL: ${{ secrets.THOUGHTSPOT_URL }}
              CS_TOOLS_THOUGHTSPOT__USERNAME: ${{ secrets.THOUGHTSPOT_USERNAME }}
              CS_TOOLS_THOUGHTSPOT__SECRET_KEY: ${{ secrets.THOUGHTSPOT_SECRET_KEY }}
              # CS_TOOLS_TEMP_DIR: ...

            runs-on: ubuntu-latest
            steps:

            - name: Set up Python 3.12
              uses: actions/setup-python@v4
              with:
                python-version: 3.12

            - name: Install a specific version of CS Tools
              run: python -m pip install https://github.com/thoughtspot/cs_tools/archive/v1.5.0.zip[cli]

            # --config ENV:   tells CS Tools to pull the information from environment variables.
            - name: Run your CS Tools Command
              run: "cs_tools config check --config ENV:"
        ```

## Closing Thoughts

And that's it! Now you have all the tools (pun fully intended :wink:) you need to be able to get up and running with the
__CS Tools__ project. Be sure to check out the rest of the documentation, and also find us on __ThoughtSpot Community__.

<div class=grid-define-columns data-columns=4 markdown="block">
[:octicons-tools-16: All the Tools](../tools/index.md){ .md-button }

[:octicons-comment-discussion-16: Chat with us](https://github.com/thoughtspot/cs_tools/discussions/55){ .md-button }

[:octicons-bug-16: Report a bug](https://github.com/thoughtspot/cs_tools/issues/new/choose){ .md-button }

[:octicons-mark-github-16: Source code](https://github.com/thoughtspot/cs_tools){ .md-button }
</div>


[cronguru]: https://crontab.guru/
[schtasks]: https://docs.microsoft.com/en-us/previous-versions/orphan-topics/ws.10/cc772785(v=ws.10)?redirectedfrom=MSDN
[github-help]: https://github.com/thoughtspot/cs_tools/issues/new/choose
[search-cs_tools]: https://community.thoughtspot.com/s/global-search/cs_tools
