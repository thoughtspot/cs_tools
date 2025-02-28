<p align="center">
  <img width="400" src="docs/assets/images/logo-transparent.png" alt='ThoughtSpot | CS Tools'>
  <br/>
  <i>🧙 Give your Admins magic powers with tools created by the <b>ThoughtSpot Customer Success Team</b>.</i>
  <br/>
  <br/>
  <b>Learn more in our documentation
  <br/>
  <a href="https://thoughtspot.github.io/cs_tools/">
    Getting started with CS Tools
  </a>
  </b>
</p>

## Features
- Explore your ThoughtSpot platform data with the [__Searchable Liveboards__](https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#searchable)
- Clean stale and forgotten Answers and Liveboards with [__Archiver__](https://thoughtspot.github.io/cs_tools/generated/cli/reference.html#archiver)
- Extract your ThoughtSpot data to popular formats with [__Syncers__](https://thoughtspot.github.io/cs_tools/syncer/what-is/)
- Multi-platform support (connect to your __Dev__, __QA__, and __Prod__!)
- Supports the latest ThoughtSpot version on Software & Cloud
- Install anywhere: Windows, MacOS, Linux, and serverless
- Scheduler-friendly execution, set it and forget it!

---

> [!IMPORTANT]
>  While **CS Tools** is maintained by members of the __ThoughtSpot__ team, they are __TOTALLY FREE__!
>
> ❗ __ThoughtSpot [Support Team](https://community.thoughtspot.com/__ will be unable to help you resolve any issues.
>
> :bulb: __Feature Requests__ and :ring_buoy: __Support__ are handled [__here on Github Discussions__](https://github.com/thoughtspot/cs_tools/discussions).
>

---

## Installation

Please see the [__Getting Started guide in our documentation__](https://thoughtspot.github.io/cs_tools/getting-started/).

## Development Installation

__CS Tools__ uses `uv` ([__docs__](https://docs.astral.sh/uv/)) to manage its dependencies. Once you have cloned the
repository, run the following command from the root of the repository to setup your development environment:

```bash
uv pip install -e .[dev,docs]
```

Please see [__CONTRIBUTING.md__](./CONTRIBUTING.md) for details on how to contribute to the __CS Tools__ project.

---

<sub><b>Workflow Automation</b></sub>

📜
[![Deploy docs to GH Pages](https://github.com/thoughtspot/cs_tools/actions/workflows/build-docs.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/build-docs.yaml)

🧪
[![Test CS Tools Bootstrapper](https://github.com/thoughtspot/cs_tools/actions/workflows/test-bootstrapper.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/test-bootstrapper.yaml)

🧰
[![Extract Metadata](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-metdata.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-metdata.yaml)
[![Extract BI Server](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-bi-data.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-bi-data.yaml)
[![Extract Audit Logs](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-audit-logs.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-audit-logs.yaml)
[![Extract TML](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-tml.yaml/badge.svg)](https://github.com/thoughtspot/cs_tools/actions/workflows/fetch-tml.yaml)
