from ward import fixture
import typer.testing

import cs_tools.cli.main as main


@fixture
def runner():
    return typer.testing.CliRunner()


@fixture
def entrypoint():
    # setup work
    main._setup_tools(main.tools_app, ctx_settings=main.app.info.context_settings)
    main.app.add_typer(main.tools_app)
    main.app.add_typer(main.cfg_app)
    main.app.add_typer(main.log_app)
    return main.app
