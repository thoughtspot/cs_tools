!!! note

    It is recommended that you read [Setup a Configuration File][config-files]{ .internal-link } before proceeding with scheduling a CS Tool.

We have many built-in tools on both the [client-hosted][sw-sys-ws]{ target='secondary' .external-link } and [cloud][cl-sys-ws]{ target='secondary' .external-link } deployments of ThoughtSpot that make internal platform data available for Search.

However, these data are not always accessible for your individual use case and can oftentimes be difficult to share with other users in the platform.

A common workflow for many of our tools is to capture some data from the ThoughtSpot API, feed it into your database backend, and ingest that data back into ThoughtSpot to later be consumed in Search.

You can use various the [advanced tools][adv-tools]{ target='secondary' .external-link } in `cs_tools` to do exactly this, and pair it up with your favorite scheduling utility like `cron` or Windows's own Task Scheduler. Below are some examples on how to schedule the [Searchable: Users & Groups][tool-sug]{ target='secondary' .external-link } tool to pull user and group data out of ThoughtSpot and push it directly into Falcon[^1].


=== ":fontawesome-brands-apple:, :fontawesome-brands-linux: crontab"

    !!! hint "Need help?"

        [https://crontab.guru][cronguru]{ target='secondary' .external-link }

        *A helpful online utility for writing your cron schedule expressions.*
    
    ```cron
    # Daily at 3:05am
     5   3   *   *   *  source /full/path/to/unix_activate.sh && cs_tools tools searchable-user-groups --config ts-namey

    # Every 2hrs at 15 minutes past the hour
    15  */2  *   *   *  source /full/path/to/unix_activate.sh && cs_tools tools searchable-user-groups --config ts-namey
    ```

=== ":fontawesome-brands-windows: Task Scheduler"

    !!! info "Need help?"

        [Windows Documentation][schtasks]{ target='secondary' .external-link }

        *Reference document for the task scheduler command line utility.*

    ```terminal
    # Daily at 3:05am
    schtasks /create ^
             /tn cs_tools ^
             /sc DAILY    ^
             /st 03:05    ^
             /tr \\full\path\to\windows_activate.ps1 && cs_tools tools searchable-user-groups gather --config trial

    # Every 2hrs at 15 minutes past the hour
    schtasks /create ^
             /tn cs_tools ^
             /sc MINUTE   ^
             /mo 120      ^
             /st 00:15    ^
             /tr \\full\path\to\windows_activate.ps1 && cs_tools tools searchable-user-groups gather --config trial
    ```


[^1]:
    Falcon is ThoughtSpot's proprietary in-memory database that is only available on legacy platform configurations. Consult the tool's documentation page for additional tips on how to make this data available to the various supported [Cloud Data Warehouses][cl-embrace]{ target='secondary' .external-link } that ThoughtSpot connects to.

[adv-tools]: ../../overview#advanced-tools
[cl-sys-ws]: https://cloud-docs.thoughtspot.com/admin/system-monitor/worksheets.html
[cl-embrace]: https://cloud-docs.thoughtspot.com/admin/ts-cloud/embrace.html
[config-files]: ../configuration-file
[cronguru]: https://crontab.guru/
[schtasks]: https://docs.microsoft.com/en-us/previous-versions/orphan-topics/ws.10/cc772785(v=ws.10)?redirectedfrom=MSDN
[sw-sys-ws]: https://docs.thoughtspot.com/latest/admin/system-monitor/worksheets.html
[tool-sug]: ../../searchable-user-groups
