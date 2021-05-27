<p align="center">
  <a href="https://www.thoughtspot.com/">
    <img width="350" height="208" src="./docs/img/logo_black.svg?token=ADMI6NPEWE7ZDGUQMPFLGUC7HWK5E" alt='ThoughtSpot'>
  </a>
</p>

<p align="center"><strong>CS Tools</strong> <em>- field engineering tooling tuned for
customer delight.</em></p>

CS Tools is an initiative by the CS/PS team to collect, organize, analyze, improve, and
streamline various field engineering tools existing today. This repository was
introduced to form consistency in how we design and distribute our tools.

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
[Python 3.6.8][install-python] or greater installed on your computer. The shortlist of
instructions are below!

From your command line:
```console
$ cd $HOME
$ python3 -m venv .cs_tools-dev
$ source .cs_tools-dev/bin/activate
$ pip install -e git+https://github.com/thoughtspot/cs_tools.git
```

That's it!

## Our Tools

All tools currently live within the ThoughtSpot library as a subpackage. This allows for
ease of distribution and install at a customer site, or along with a customer.

Nearly all tools depend on the ThoughtSpot API directly in order to function properly,
please see our [Install Instructions][dist] for how to set up a client with the CT Tools
library and toolset.

For further reading about tool structure, please see the [tools README][tools-readme].

[slack-channel]: https://slack.com/app_redirect?channel=cstools
[install-git]: https://git-scm.com/downloads
[install-python]: https://www.python.org/downloads
[tools-readme]: ./cs_tools/tools/README.md
[dist]: ./dist/README.md
