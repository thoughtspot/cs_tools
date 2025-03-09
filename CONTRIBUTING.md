# Feedback and Contribution

We welcome any input, feedback, bug reports, and contributions via
[__CS Tools__'s GitHub Repository](http://github.com/thoughtspot/cs_tools/).

All contributions, suggestions, and feedback you submitted are accepted under the [__Project's license__](./LICENSE). You
represent that if you do not own copyright in the code that you have the authority to submit it under the
[__Project's license__](./LICENSE). All feedback, suggestions, or contributions are not confidential.

---

### SECTIONS

> - [Project Philosophy](#architecture-philosophy)
> - [Setup Your Environment](#setting-up-your-environment)
> - [Git flow / Branch Strategy](#creating-a-branch)
> - [Writing Documentation](#how-to-contribute-documentation-to-cs-tools)
> - [Readying a Release](#readying-a-release)

---

### Architecture Philosophy

This section aims to describe the project layout and some of the core architecture decisions that were made to support the development of __CS Tools__. Below is a diagram of the main subpackages of __CS Tools__.

Each subsection undernearth will discuss its purpose. This is not meant to be an exhaustive list of all the patterns found in __CS Tools__, but to kickstart development and understanding within each section of the overall codebase.

```shell
src/cs_tools/
├─ api/
|  ├─ workflows/
|  └─ client.py
|
├─ cli/
|  ├─ commands/
|  ├─ dependencies/
|  ├─ tools/
|  └─ custom_types.py
|
├─ sync/
├─ updater/
|   
├─ __main__.py
├─ programmatic.py
└ ...
```

*\*\* each of these subpackages (and `cs_tools` itself) may define a `utils.py`, think of them as locally-scoped helper functions.*

#### API

Most of what CS Tools does is to interact with the __ThoughtSpot__ [__V2 REST APIs__](https://developers.thoughtspot.com/docs/rest-apis). This means that the majority of the time, __CS Tools__ is simply waiting on the __ThoughtSpot__ server to respond with data. For this reason, the entire [__HTTP Client__](./cs_tools/api/client.py) is written using `asyncio` with [`httpx`](https://github.com/encode/httpx/). This uses an equivalent pattern to the __Javascript__ `Promise` interface.

This pattern is often is difficult for __Python__ developers to adopt to. We have provided wrappers in order to run the asynchronous client endpoints in a synchronous manner.

Below is a small example of how to use `utils.run_sync`. You will also find `utils.bounded_gather` (similar to `Promise.all()` or `Promise.allSettled()` depending on the value passed to `return_exceptions: bool`, respectively.)

```python
from cs_tools import utils
from cs_tools.api.client import RESTAPIClient

http = RESTAPIClient()
coro = http.get("/")         # ==> types.Coroutine
resp = utils.run_sync(coro)  # ==> httpx.Response
data = resp.json()           # ==> dict[str, Any]
```

Additionally, we have `api.workflows`, which are bundles of logic which may span one or more endpoints. These implement common business logic that customers may write that the V2 APIs do not provide natively.

#### CLI

This is the "User Interface" of __CS Tools__. Separating out the `cli` subpackage from the rest of the codebase allows for re-use of __CS Tools__ `api` layer in other projects. The main dependency of the CLI layer is [__Typer__](https://github.com/fastapi/typer), which was chosen for it's typehint-friendly interface, signalling strong intent to other developers as to what is expected from our users on the terminal.

The `cli` subpackage has two main goals..

1. Provide a set of "tools" focused on giving customers stronger control over their __ThoughtSpot__ cluster
2. Bring order to the chaos that is an unstructured terminal environment across operating systems

Tools implement larger, opinionated bit of business logic and may be written in a synchronous or asynchronous pattern. The magic of this lies in [`cli.ux.AsyncTyper`](./cs_tools/cli/ux.py), which defines wraps all callbacks and commands in an opposite interface to `utils.run_sync`.

You will find the CLI main entrypoint under [`cs_tools/cli/commands/main.py`](cs_tools/cli/commands/main.py) as the `run` function.

Under the `cli` subpackage, you will also find two more key pieces..

- `dependencies/` - a way to provide simple dependency injection to __Typer__ commands
- `custom_types.py` - a way to validate and convert raw cli input into marshalled types

The minimum required pattern for a directory to be considered a CSTool is defined under [`programmatic.py`](./cs_tools/programmatic.py).

```python
    # REQUIRED VARIABLES TO BE CONSIDERED A VALID CS TOOL.
    for var in ("app", "__version__"):
        assert hasattr(module, var), f"CS Tool '{self.directory}' must export the variable '{var}' in __init__.py"
```

For a concise example of a tool, see the [__Extractor__](cs_tools/cli/tools/extractor/app.py), a tool which wraps the [__Search Data API__](https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fdata%2Fsearch-data) and allows a user to mirror that tabular data over to their database.

#### Sync[er]

Speaking of tabular data, the vast majority of the __ThoughtSpot__ experience sits on top of the database, without storing the customer data itself. __CS Tools__ often times extracts and manipulates that metadata at scale -- across the entire platform. __Syncers__ act as the glue between the __ThoughtSpot__ system, the runtime environment (local machine), and the Database.

It is probably easy to grok what a Syncer is from [the official documentation](https://thoughtspot.github.io/cs_tools/syncer/what-is/).

__Syncers__ are not meant to be exhaustive database wrappers, and only offer simple `READ / WRITE` to popular tabular formats. Syncers provider their requirements in a local `MANIFEST.json` which strictly adheres to the interface at [`cs_tools/sync/base.py`](cs_tools/sync/base.py).

For a simple example of a Syncer, see the [__Excel Syncer__](cs_tools/sync/excel/syncer.py).

#### Updater

Our users are not developers and our users are not developers. The terminal is a scary place for folks who don't write code, so we provide a bootstrapper / install script to ease the friction of getting started.

Because we aim to be responsible developers, __CS Tools__ manages its own isolated virtual environment. The majority of this initiative is actually handled by a clever combination of [`venv`](https://docs.python.org/3/library/venv.html) for initial creation and [`uv`](https://docs.astral.sh/uv/) for ongoing maintenance.

Additionally in this subpackage is a way of abstracting management of the `PATH` variable on all operating systems. This is the mechanism which provides the "global" `cs_tools` command so that uers never even have to know we're wizards behind a curtain :mage:.

---

### Setting Up Your Environment

Fork the __CS Tools__ repository on GitHub and then clone the fork to your local machine. For more details on forking see the [__GitHub Documentation__](https://help.github.com/en/articles/fork-a-repo).

```bash
git clone https://github.com/YOUR-USERNAME/cs_tools.git
```

To keep your fork up to date with changes in this repo, you can [__use the fetch upstream button on GitHub__](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork).

__CS Tools__ uses `uv` ([__docs__](https://docs.astral.sh/uv/)) to manage its dependencies. Once you have cloned the repository, run the following command from the root of the repository to setup your development environment:

```bash
cd cs_tools/
uv pip install -e ".[dev]"
uv run hatch run dev:setup
```

Now you can install the latest version of __CS Tools__ locally using `pip`. The `-e` flag indicates that your local changes will be reflected every time you open a new Python interpreter (instead of having to reinstall the package each time).

`[dev]` indicates that pip should also install the development requirements which you can find in `pyproject.toml` (`[project.optional-dependencies]/dev`)

`pre-commit install` installs the [__pre-commit__](https://pre-commit.com/) hook which will automatically check your code for issues before committing. To run the checks locally, run `uv run pre-commit run --all-files`.

### Creating a Branch

Once your local environment is up-to-date, you can create a new git branch, from `dev`, which will contain your contribution (always create a new branch instead of making changes to the main branch):

```bash
git switch -c <your-branch-name> dev
```

With this branch checked-out, make the desired changes to the package.

### Creating a Pull Request

When you are happy with your changes, you can commit them to your branch by running

```bash
git add <modified-file>
git commit -m "Some descriptive message about your change"
git push origin <your-branch-name>
```

You will then need to submit a pull request (PR) on GitHub asking to merge your example branch into the main __CS Tools__ repository. For details on creating a PR see GitHub documentation [__Creating a pull request__](https://help.github.com/en/articles/creating-a-pull-request).

You can add more details about your example in the PR such as motivation for the example or why you thought it would be  a good addition. You will get feedback in the PR discussion if anything needs to be changed. To make changes continue to push commits made in your local example branch to origin and they will be automatically shown in the PR.

Hopefully your PR will be answered in a timely manner and your contribution will help others in the future.

---

### How To Contribute Documentation to CS Tools

__CS Tools__ documentation is written in [__Markdown__](https://www.markdownguide.org/getting-started/) and compiled into html pages using [__Material for MkDocs__](https://squidfunk.github.io/mkdocs-material/). Contributing to the documentation 
requires some extra dependencies.

```bash
uv pip install -e ".[docs]"
```

Set your environment variables so that the generated documentation (`hooks/cli_reference_generator.py`) can be built against a valid ThoughtSpot cluster.

<details>
  <summary><b>Windows</b></summary>

  ```bash
  $env:CS_TOOLS_THOUGHTSPOT__URL = "https://<YOUR-THOUGHTSPOT-CLUSTER>.thoughtspot.cloud"
  $env:CS_TOOLS_THOUGHTSPOT__USERNAME = "<YOUR-THOUGHTSPOT-USERNAME>"
  $env:CS_TOOLS_THOUGHTSPOT__PASSWORD = "<YOUR-THOUGHTSPOT-PASSWORD>"
  ```
</details>

<details>
  <summary><b>POSIX (Mac, Linux)</b></summary>

  ```bash
  CS_TOOLS_THOUGHTSPOT__URL = "https://<YOUR-THOUGHTSPOT-CLUSTER>.thoughtspot.cloud"
  CS_TOOLS_THOUGHTSPOT__USERNAME = "<YOUR-THOUGHTSPOT-USERNAME>"
  CS_TOOLS_THOUGHTSPOT__PASSWORD = "<YOUR-THOUGHTSPOT-PASSWORD>"
  ```
</details>

Note that the [__CS Tools__ website](https://thoughtspot.github.io/cs_tools/) is only updated when a new version is released so your contribution might not show up for a while.

To build the documentation locally, you can use the following commands:

```bash
uv run hatch run docs:serve
```

To view the documentation, open your browser and go to `http://localhost:8000`. To stop the server, use `^C` (control+c) in the terminal.

> [!IMPORTANT]
>  New commands are automatically documented!
>
> The [__CLI Reference page__](https://thoughtspot.github.io/cs_tools/generated/cli/reference.html) is generated from the command line itself.
>
> *\* see [`docs/hooks/cli_reference_generator.py`](./docs/hooks/cli_reference_generator.py) for implementation details.*
>

---

### Readying a Release

Once changes have been coordinated back to the `dev` or coordination / integration branch (a release-branch like `v1.6.5`). They will need be merged to `master` and a release published in order to be accessible to users.

Before merging to `master`, ensure you have a commit bumping the version of the project to reflect new changes. We bias towards [__semantic versioning__](https://semver.org/) in __CS Tools__, with `micro` versions being assigned to bugfixes or small enhancements, and `minor` versions for large features, new tools, or general backwards incompatibility.

Once all changes are merged to `master`, two GitHub Action workflows will automatically run.

- [__to ensure the `updater/_bootstrapper.py` script functions__](.github/workflows/test-bootstrapper.yaml) across all supported architecture
- [__to build and push the documentation__](.github/workflows/test-bootstrapper.yaml) out to __https://thoughtspot.github.io/cs_tools/__

\*\**note, the GitHub runner for testing the bootstrapper is flaky, and may need be run several times to before all jobs will succeed.*

> [!IMPORTANT]
>  Releases need to be tagged as `vX.Y.Z` with __no exceptions__! This is a strict version pattern.
>

Finally, all that is left is to tag the latest commit on `master`, and write a [__Release Notes__](https://github.com/thoughtspot/cs_tools/releases), marking the release as the latest release.

---
<center>

### Congrats on releasing __CS Tools__! :relaxed::heart:

</center>

---