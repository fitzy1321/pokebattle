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

__generated_with = "0.23.5"
app = marimo.App(width="columns")


@app.cell(column=0)
def utils():
    import marimo as mo
    import requests

    # import os
    @mo.persistent_cache
    def request_pokeapi(url: str):
        print("fetching data form api")
        result = requests.get(url)
        if not result.ok:
            raise RuntimeError(
                f"Something went wrong fetching pokeapi data. {result.status_code} {result.raw}"
            )
        return result.json()

    return mo, request_pokeapi


@app.cell(column=1)
def _(request_pokeapi):
    # mo.stop(
    #     predicate=not gen_1_rbtn.value, output=mo.md("Click 👆 to run this cell")
    # )

    gen_1_data = request_pokeapi("https://pokeapi.co/api/v2/generation/1")
    gen_1_data
    return (gen_1_data,)


@app.cell
def _(gen_1_data):
    move_urls = [m["url"] for m in sorted(gen_1_data["moves"], key=lambda x: x["name"])]
    move_urls
    return


@app.cell
def _(gen_1_data):
    pokemon_urls = [p["url"] for p in gen_1_data["pokemon_species"]]
    pokemon_urls
    return


@app.cell(hide_code=True)
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
        mo.md("Expensive network and parsing operation. Click 👆 to run this cell"),
    )

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
        mo.md("Expensive network and parsing operation. Click 👆 to run this cell"),
    )

    move_data = request_pokeapi("https://pokeapi.co/api/v2/move/1")
    move_data
    return


@app.cell
def _():
    import sqlalchemy

    DATABASE_URL = "sqlite:///pokedata.db"
    engine = sqlalchemy.create_engine(DATABASE_URL)
    return


@app.cell
def _():
    return


@app.cell(column=2)
def _():
    import marimo as mo

    run_full_fetch_btn = mo.ui.run_button()
    run_full_fetch_btn
    return mo, run_full_fetch_btn


@app.cell
def _(mo, run_full_fetch_btn):
    mo.stop(
        not run_full_fetch_btn.value,
        mo.md(
            "This will run multiple get requests against the pokeapi. Do not run this often"
        ),
    )

    return


if __name__ == "__main__":
    app.run()
