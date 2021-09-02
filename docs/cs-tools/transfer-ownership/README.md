# Transfer Ownership

This solution allows the customer to transfer all objects from one user to another.

This is a very simple tool. The API call it uses will **only** transfer all objects from
one single user to another single user.

One use case for this tool is when an employee has left the company, but their
ThoughtSpot content needs to be saved. In this case, you may transfer all their created
content to another designated owner.

## CLI preview

```console
(.cs_tools) C:\work\thoughtspot\cs_tools>cs_tools tools transfer-ownership --help
Usage: cs_tools tools transfer-ownership [OPTIONS] COMMAND [ARGS]...

  Transfer ownership of all objects from one user to another.

Options:
  --version   Show the tool's version and exit.
  --helpfull  Show the full help message and exit.
  -h, --help  Show this message and exit.

Commands:
  transfer  Transfer ownership of all objects from one user to another.
```
