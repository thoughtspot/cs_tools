# need to reroute to cli.main
# - this is for the case where the cs_tools.exe gets purged in some corporate environments, but venv works fine
#
# check if [cli] installed, route to cs_tools.cli.main:run
# if not, ... raise an error ? what happens if main isn't defined ? warnings.warn for cli not installed ?
