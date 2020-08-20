<p align="center">
  <a href="https://www.thoughtspot.com/">
    <img width="350" height="208" src="./docs/img/logo_black.svg?token=ADMI6NPEWE7ZDGUQMPFLGUC7HWK5E" alt='ThoughtSpot'>
  </a>
</p>

<p align="center"><strong>CS Tools</strong> <em>- field engineering tooling tuned for
customer delight.</em></p>

CS Tools is an initiative by the CS/PS team to collect, organize, analyze, improve, and
streamline various field engineering tools existing today. This repository is introduced
to form consistency in how we design, build, test, document, and distribute our tools.
In doing so, we are able to streamline our work as well as provide our customers with
the highest level of consultancy that they've come to expect from the team.

---

## Rule #1: <font color="green">Everyone Can Participate!</font>

We strongly believe everyone in CS/PS can participate, no matter what their technical
proficiency is. Whether you want to act as part of the steering council that decides
the direction of the overall project, be a field expert and liaise between developers
and our customers, roll your sleeves up and git dirty developing new features or
squashing bugs, or even help communicate the cool things the project has accomplished by
writing snappy documentation - rest assured there will be plenty of tasks to participate
in!

Not sure where to start? Come chat with us in #cstools on [Slack][slack-channel]!

## Getting Started

To clone and work this library, you'll want to have [Git][install-git] and
[Python 3.6.1][install-python] or greater installed on your computer. Then, create a
virtual environment and activate it. <sup>([Don't know how to do that][bp-venv]?)</sup>

From your command line:
```console
$ pip install git+https://github.com/thoughtspot/cs_tools.git

-or-

$ poetry add git+https://github.com/thoughtspot/cs_tools.git
$ poetry install
```

That's it!

P.S. - for extra credit, don't forget to check out our [best practices][bp-main]!

## Our Tools

Note: All tools currently live alongside the ThoughtSpot library as an implementation
detail. Our current structure will aid us in separating off these tools at a later date.

All CS tools are installed as part of the Github CS Tools library. They do not live
under the `/thoughtspot` directory so that they may be shared with clients directly.
All tools do however, depend on the ThoughtSpot library in order to function properly,
please see [Best Practices: Client Install][bp-client-install] for how to set up a
client with the ThoughtSpot library.

For further reading about tool structure, please see the [tools README][tools-readme].

[slack-channel]: https://slack.com/app_redirect?channel=cstools
[install-git]: https://git-scm.com/downloads
[install-python]: https://www.python.org/downloads
[bp-main]: ./best-practices/
[bp-venv]: ./best-practices/virtual-environment.md
[bp-client-install]: ./best-practices/client-install.md
[tools-readme]: ./tools/README.md
