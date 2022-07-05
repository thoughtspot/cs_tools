<style>
  /* Hide the "Edit on Github" button */
  .md-content__button { display: none; }

  /* Hide the Next button in the footer (so the tutorial has a logical conclusion) */
  .md-footer__link--next { display: none; }
</style>

# Scheduling with __CS Tools__

__Archiver__{ .fc-purple } is a powerful tool in your arsenal as a __ThoughtSpot__ administrator. In order to take full
advantage of it, you'll want to schedule it to run regularly.

It can be helpful to keep close tabs on the amount of stale content that exists in your platform. Let's schedule our
__Archiver__{ .fc-purple } identification report to export from the platform once every week.


## Write a little program

For the sake of example, we'll use this little program below to first run our command, and then count the number of
lines in the file that start with "__answer__". This will act as an approximation for how much content is growing stale
over time.

??? info "Why so simple?"

    Naturally your use case will be more complex, like writing this data to a database table and running alerting or
    exposing that data back into __ThoughtSpot__ for example. While those use cases are important, they are outside the
    scope of this tutorial.

=== ":fontawesome-brands-windows: Windows"

    For the sake of example, these are the contents of a Powershell script in your Downloads folder called `counter.ps1`

    ```powershell
    cs_tools tools archiver identify --report csv://default `
    ; Select-String -Path %USERPROFILE%/Downloads/archiver-report.csv -Pattern '^answer' `
    | Measure-Object -Line
    ```

=== ":fontawesome-brands-apple:, :fontawesome-brands-linux: Mac, Linux"

    For the sake of example, these are the contents of a bash script in your Downloads folder called `counter.sh`

    ```bash
    cs_tools tools archiver identify --report csv://default \
    | sed -e '1d' -e '/^answer/!d' $HOME/Downloads/archiver-report.csv \
    | wc -l
    ```

!!! question "Should I always write a file for my commands?"

    __You <span class=fc-coral>don't need to</span> wrap your commands in a file__ and pass that to your scheduling
    utility.

    This is a just a common convention you will see when dealing with schedulers. If the __CS Tools__ command doesn't
    need any follow-up, because it's inserting records into a database table or syncing Users, then you can schedule the
    naked command directly in the scheduling application.

    __The choice is totally yours!__{ .fc-blue }


## Schedule it

Now that we've decided how to track our content, we're ready to schedule our command to run weekly.

=== ":fontawesome-brands-windows: Task Scheduler"

    !!! info "Need help?"

        [Windows Documentation][schtasks]{ target='secondary' .external-link }

        *Reference document for the task scheduler command line utility.*

    ```console
    # Weekly, on Monday at 3:05am
    schtasks /create ^
             /tn cs_tools ^
             /sc WEEKLY   ^
             /d  MON      ^
             /st 03:05    ^
             /tr %USERPROFILE%/Downloads/counter.ps1
    ```

=== ":fontawesome-brands-apple:, :fontawesome-brands-linux: crontab"

    !!! hint "Need help?"

        [https://crontab.guru][cronguru]{ target='secondary' .external-link }

        *A helpful online utility for writing your cron schedule expressions.*
    
    ```cron
    # Weekly, on Monday at 3:05am
     5  3  *  *  1  $HOME/Downloads/counter.sh
    ```


## Closing Thoughts

And that's it! Now you have all the tools (pun fully intended :wink:) you need to be able to get up and running with the
__CS Tools__ project. Be sure to check out the rest of the documentation, and also find us on __ThoughtSpot Community__.

  - [__All the Tools__][docs-tools]
  - [__Get Help__][google-form-help]
  - [__GitHub Issues__][github-help]
  - [__ThoughtSpot Community__][search-cs_tools]


[cronguru]: https://crontab.guru/
[schtasks]: https://docs.microsoft.com/en-us/previous-versions/orphan-topics/ws.10/cc772785(v=ws.10)?redirectedfrom=MSDN
[docs-tools]: ../cs-tools/overview.md
[google-form-help]: https://forms.gle/Tmbs6ZhsZa2DMFsU9
[github-help]: https://github.com/thoughtspot/cs_tools/issues/new/choose
[search-cs_tools]: https://community.thoughtspot.com/s/global-search/cs_tools
