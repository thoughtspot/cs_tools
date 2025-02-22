# Feedback and Contribution

We welcome any input, feedback, bug reports, and contributions via
[__CS Tools__'s GitHub Repository](http://github.com/thoughtspot/cs_tools/).

All contributions, suggestions, and feedback you submitted are accepted under the [__Project's license__](./LICENSE). You
represent that if you do not own copyright in the code that you have the authority to submit it under the
[__Project's license__](./LICENSE). All feedback, suggestions, or contributions are not confidential.

### Setting Up Your Environment

Fork the __CS Tools__ repository on GitHub and then clone the fork to you local machine. For more details on forking
see the [__GitHub Documentation__](https://help.github.com/en/articles/fork-a-repo).

```bash
git clone https://github.com/YOUR-USERNAME/cs_tools.git
```

To keep your fork up to date with changes in this repo, you can [__use the fetch upstream button on 
GitHub__](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork).

__CS Tools__ uses `uv` ([__docs__](https://docs.astral.sh/uv/)) to manage its dependencies. Once you have cloned the
repository, run the following command from the root of the repository to setup your development environment:

```bash
cd cs_tools/
uv pip install -e ".[dev]"
uv run hatch run dev:setup
```

Now you can install the latest version of __CS Tools__ locally using `pip`. The `-e` flag indicates that your local
changes will be reflected every time you open a new Python interpreter (instead of having to reinstall the package each
time).

`[dev,docs]` indicates that pip should also install the development and documentation requirements which you can find 
in `pyproject.toml` (`[project.optional-dependencies]/dev` and `[project.optional-dependencies]/docs`)

`pre-commit install` installs the [__pre-commit__](https://pre-commit.com/) hook which will automatically check your code
for issues before committing. To run the checks locally, run `uv run pre-commit run --all-files`.

### Creating a Branch

Once your local environment is up-to-date, you can create a new git branch which will contain your contribution (always
create a new branch instead of making changes to the main branch):

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

You will then need to submit a pull request (PR) on GitHub asking to merge your example branch into the main
__CS Tools__ repository. For details on creating a PR see GitHub documentation [__Creating a pull
request__](https://help.github.com/en/articles/creating-a-pull-request).

You can add more details about your example in the PR such as motivation for the example or why you thought it would be 
a good addition. You will get feedback in the PR discussion if anything needs to be changed. To make changes continue 
to push commits made in your local example branch to origin and they will be automatically shown in the PR.

Hopefully your PR will be answered in a timely manner and your contribution will help others in the future.

## How To Contribute Documentation to CS Tools

__CS Tools__ documentation is written in [__Markdown__](https://www.markdownguide.org/getting-started/) and compiled into 
html pages using [__Material for MkDocs__](https://squidfunk.github.io/mkdocs-material/). Contributing to the documentation 
requires some extra dependencies.

```bash
uv pip install -e ".[docs]"
```

Note that the [__CS Tools__ website](https://thoughtspot.github.io/cs_tools/) is only updated when a new version is
released so your contribution might not show up for a while.

To build the documentation locally, you can use the following commands:

```bash
uv run hatch run docs:serve
```

To view the documentation, open your browser and go to `http://localhost:8000`. To stop the server, use `^C` 
(control+c) in the terminal.

> [!IMPORTANT]
>  New commands are automatically documented, as the [CLI Reference page](https://thoughtspot.github.io/cs_tools/generated/cli/reference.html) is generated from the command line itself.
>
> See [docs/hooks/cli_reference_generator.py](./docs/hooks/cli_reference_generator.py) for implementation details.
>

---
