# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.23.5",
#     "polars==1.40.1",
#     "requests==2.33.1",
# ]
# ///

import marimo

__generated_with = "0.23.5"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import requests

    # import os
    return mo, requests


@app.cell
def _(mo, requests):
    @mo.persistent_cache
    def request_pokeapi(url: str):
        print("fetching data form api")
        result = requests.get(url)
        if not result.ok:
            raise RuntimeError(
                f"Something went wrong fetching pokeapi data. {result.status_code} {result.raw}"
            )
        return result.json()

    return (request_pokeapi,)


@app.cell
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


@app.cell
def _(mo):
    run_button = mo.ui.run_button()
    run_button
    return (run_button,)


@app.cell
def _(mo, request_pokeapi, run_button):
    # Stop execution if the button hasn't been clicked
    mo.stop(not run_button.value, mo.md("Click 👆 to run this cell"))

    data = request_pokeapi("https://pokeapi.co/api/v2/pokemon/1")
    data
    return


if __name__ == "__main__":
    app.run()
