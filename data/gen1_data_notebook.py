# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.23.8",
#     "requests==2.34.2",
# ]
# ///

# pyright: reportUnusedExpression=false

import marimo

__generated_with = "0.23.9"
app = marimo.App(width="columns")


@app.cell(column=0)
def _():
    import json
    import time
    from functools import lru_cache
    from pathlib import Path
    from typing import Any

    import marimo as mo
    import requests

    DELAY = 0.3

    POKE_ID_MAX = 151

    @lru_cache(maxsize=None)
    def requests_get(url: str) -> requests.Response:
        time.sleep(DELAY)
        return requests.get(url, timeout=10)


    def requests_pokeapi(url: str) -> dict:
        """GET with basic error handling. Cached by URL — repeated calls are free."""
        resp = requests_get(url)
        if not resp.ok:
            print(
                f"Error fetching from api, HTTP Code: {resp.status_code}. {resp.raw}"
            )
            return {}

        return resp.json()


    def open_json_file(filename: str | Path) -> Any:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    return POKE_ID_MAX, mo, open_json_file, requests_get, requests_pokeapi


@app.cell
def _(POKE_ID_MAX, mo, open_json_file):
    import base64


    data = open_json_file('compiled_pokemon_data.json')
    # image = base64.b64decode(data[0]["front_sprite"])
    [(mo.image(base64.b64decode(data[i]["front_sprite"])),mo.image(base64.b64decode(data[i]["back_sprite"]))) for i in range(1,POKE_ID_MAX)]
    return


@app.cell(column=1, hide_code=True)
def _(mo):
    mo.md(r"""
    ## The next several cells will hit make network requests

    Click the run button below to 'fire' them off.
    """)
    return


@app.cell
def _(mo):
    # marimo run button, good to block off expensive cells
    poke_run_btn = mo.ui.run_button()
    poke_run_btn
    return (poke_run_btn,)


@app.cell
def _(mo, poke_run_btn, requests_pokeapi):
    mo.stop(
        not poke_run_btn.value,
        mo.md("☝️ Click button for 'expensive' api calls"),
    )

    # get move data for bulbasaur
    # move_data = requests_pokeapi("https://pokeapi.co/api/v2/move/1")
    # move_data

    # get poke-api data for bulbasaur, all generations
    poke_data = requests_pokeapi("https://pokeapi.co/api/v2/pokemon/1")
    poke_data
    return


@app.cell
def _(mo, poke_run_btn, requests_get):
    mo.stop(not poke_run_btn.value, "idcmbffj?")
    poke_sprites = {
        i: (
            mo.image(
                requests_get(
                    f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/{i}.png"
                ).content
            ),
            mo.image(
                requests_get(
                    f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/back/{i}.png"
                ).content
            ),
        )
        for i in range(1, 152)
    }
    # for i in range(1, 6):
    #     png_resp = requests_get(
    #         f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/{i}.png"
    #         # f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/back/{i}.png"
    #     )
    #     if png_resp.headers["content-type"].startswith("image"):
    #         poke_sprites[i] = png_resp.content
    #     else:
    #         print("http response was not a png image")
    # [mo.image(src=poke_sprites[i]) for i in poke_sprites.keys()]
    poke_sprites
    return


if __name__ == "__main__":
    app.run()
