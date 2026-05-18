# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "duckdb==1.5.2",
#     "marimo>=0.23.6",
#     "polars==1.40.1",
#     "requests==2.34.0",
#     "sqlalchemy==2.0.49",
#     "sqlglot==30.7.0",
# ]
# ///

# pyright: reportUnusedExpression=false

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="columns")


@app.cell(column=0)
def _():
    import marimo as mo
    import requests
    import json
    import os
    from pathlib import Path
    from typing import Any


    @mo.persistent_cache
    def request_pokeapi(url: str):
        print("fetching data form api")
        result = requests.get(url)
        if not result.ok:
            raise RuntimeError(
                f"Something went wrong fetching pokeapi data. {result.status_code} {result.raw}"
            )
        return result.json()


    def open_json_file(filename: str | Path) -> Any:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_compiled_json(file_path: Path|str|None = None):
        if not file_path:
            file_path = Path(os.getcwd())
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if "poke_api_data" not in file_path.parts:
            file_path  = file_path / "poke_api_data"

        if "compiled_pokemon_data.json" not in file_path.parts:
            file_path = file_path / "compiled_pokemon_data.json"

        return open_json_file(file_path)

    return mo, request_pokeapi


@app.cell(column=1, hide_code=True)
def _(mo):
    mo.md(r"""
    The next 2 cells are to hit the individual pokemon endpoint.
    """)
    return


@app.cell
def _(mo):
    poke_run_btn = mo.ui.run_button()
    poke_run_btn
    return (poke_run_btn,)


@app.cell
def _(mo, poke_run_btn, request_pokeapi):
    # Stop execution if the button hasn't been clicked
    mo.stop(
        not poke_run_btn.value,
        mo.md(
            "Expensive network and parsing operation. Click 👆 to run this cell"
        ),
    )

    # gen_1_data = request_pokeapi("https://pokeapi.co/api/v2/generation/1")
    # gen_1_data

    # move_urls = [
    #     m["url"] for m in sorted(gen_1_data["moves"], key=lambda x: x["name"])
    # ]
    # move_urls

    # pokemon_urls = [p["url"] for p in gen_1_data["pokemon_species"]]
    # pokemon_urls

    poke_data = request_pokeapi("https://pokeapi.co/api/v2/pokemon/1")
    poke_data
    return


@app.cell
def _(mo):
    move_run_btn = mo.ui.run_button()
    move_run_btn
    return (move_run_btn,)


@app.cell
def _(mo, move_run_btn, request_pokeapi):
    # Stop execution if the button hasn't been clicked
    mo.stop(
        not move_run_btn.value,
        mo.md(
            "Expensive network and parsing operation. Click 👆 to run this cell"
        ),
    )

    move_data = request_pokeapi("https://pokeapi.co/api/v2/move/1")
    move_data
    return


@app.cell
def _():
    # import sqlalchemy

    # DATABASE_URL = "sqlite:///pokedata.db"
    # engine = sqlalchemy.create_engine(DATABASE_URL)
    return


if __name__ == "__main__":
    app.run()
