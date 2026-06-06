#!/usr/bin/env python3
"""
fetch_gen1.py — Gen 1 Pokémon data pipeline for a Red/Blue battle system.

Fetches all 151 Pokémon from PokéAPI and saves to SQLite. Supports a local
pickle cache so you don't have to hammer the API every time you touch the DB.

Collects for each Pokémon:
  - Base stats (HP, Attack, Defense, Sp.Atk, Sp.Def, Speed)
  - Moves learned in Red/Blue (with level, PP, power, accuracy, type, etc.)
  - Type(s) — slot 1 always present, slot 2 optional
  - Next evolutions (empty list if none, multiple if branching e.g. Eevee)
  - Base experience (XP yielded when defeated)
  - Growth rate name
  - Front and back sprites as raw PNG bytes

Usage:
  python fetch_gen1.py                            # fetch from API → save to SQLite
  python fetch_gen1.py --save-cache               # fetch from API → save cache + SQLite
  python fetch_gen1.py --save-cache --cache-only  # fetch from API → save cache only
  python fetch_gen1.py --load-cache               # load cache → save to SQLite

Trade evolutions (Kadabra, Machoke, Graveler, Haunter) are remapped to
level-up at level 36 — the common fan game standard for single-player.
"""

import pickle
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import requests
import typer

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent"
VERSION_GROUP = "red-blue"
TOTAL_POKEMON = 151
DELAY = 0.3  # seconds between API requests — be polite
TRADE_EVO_LEVEL = 36  # level trade evolutions are remapped to

CACHE_FILE = Path("pokemon_gen1_data.pkl")
DB_FILE = Path("pokedata.db")
SCHEMA_FILE = Path("POKEMON_TABLE_SCHEMAS.sql")

session = requests.Session()


@lru_cache(maxsize=None)
def _fetch(url: str) -> dict:
    """GET JSON with basic error handling. LRU-cached — repeated calls are free."""
    time.sleep(DELAY)
    resp = session.get(url)
    if not resp.ok:
        print(f"  [WARN] HTTP {resp.status_code} for {url}")
        return {}
    return resp.json()


def _get_moves(pokemon_data: dict) -> list[dict]:
    rb_moves = []
    seen: set[str] = set()

    for move_entry in pokemon_data.get("moves", []):
        for vgd in move_entry.get("version_group_details", []):
            if vgd["version_group"]["name"] == VERSION_GROUP:
                move_name = move_entry["move"]["name"]
                if move_name not in seen:
                    seen.add(move_name)
                    rb_moves.append(
                        {
                            "name": move_name,
                            "level": vgd["level_learned_at"],
                            "url": move_entry["move"]["url"],
                            "method": vgd["move_learn_method"]["name"],
                        }
                    )

    rb_moves.sort(key=lambda m: m["level"])

    detailed = []
    for m in rb_moves:
        data = _fetch(m["url"])
        if not data:
            continue
        meta = data.get("meta") or {}
        detailed.append(
            {
                "name": m["name"],
                "level_learned": m["level"],
                "learn_method": m["method"],
                "power": data.get("power"),
                "accuracy": data.get("accuracy"),
                "pp": data.get("pp"),
                "type": data["type"]["name"] if data.get("type") else None,
                "damage_class": data["damage_class"]["name"]
                if data.get("damage_class")
                else None,
                "ailment": meta.get("ailment", {}).get("name"),
                "ailment_chance": meta.get("ailment_chance"),
                "stat_changes": [
                    {"stat": sc["stat"]["name"], "change": sc["change"]}
                    for sc in data.get("stat_changes", [])
                ],
                "move_category": meta.get("category", {}).get("name"),
                "healing": meta.get("healing"),
                "drain": meta.get("drain"),
            }
        )

    return detailed


def _build_evo_entry(next_node: dict) -> dict | None:
    next_name = next_node["species"]["name"]
    details = next_node.get("evolution_details", [{}])
    detail = details[0] if details else {}

    trigger = detail.get("trigger", {}).get("name") if detail.get("trigger") else None
    min_level = detail.get("min_level")
    item = detail.get("item", {}).get("name") if detail.get("item") else None

    if trigger == "trade":
        trigger = "level-up"
        min_level = TRADE_EVO_LEVEL
        item = None

    next_poke_data = _fetch(f"{BASE_URL}/pokemon/{next_name}/")
    next_id = next_poke_data.get("id") if next_poke_data else None

    if not next_id or next_id > TOTAL_POKEMON:
        return None

    return {
        "evolves_into_id": next_id,
        "evolves_into": next_name,
        "trigger": trigger,
        "min_level": min_level,
        "item": item,
    }


def _get_next_evolutions(species_data: dict, pokemon_name: str) -> list[dict]:
    evo_chain_url = species_data.get("evolution_chain", {}).get("url")
    if not evo_chain_url:
        return []

    chain_data = _fetch(evo_chain_url)
    if not chain_data:
        return []

    def walk(node: dict, target: str) -> list[dict] | None:
        if node.get("species", {}).get("name") == target:
            return [
                e
                for child in node.get("evolves_to", [])
                if (e := _build_evo_entry(child))
            ]
        for child in node.get("evolves_to", []):
            result = walk(child, target)
            if result is not None:
                return result
        return None

    return walk(chain_data.get("chain", {}), pokemon_name) or []


def _get_sprites(poke_id: int) -> tuple[bytes | None, bytes | None]:
    front_resp = session.get(f"{SPRITE_BASE}/{poke_id}.png")
    back_resp = session.get(f"{SPRITE_BASE}/back/{poke_id}.png")

    def valid_image(resp) -> bool:
        return resp.ok and resp.headers.get("content-type", "").startswith("image")

    if not valid_image(front_resp) or not valid_image(back_resp):
        print(f"  [WARN] Sprite fetch failed for #{poke_id}")
        return None, None

    return front_resp.content, back_resp.content


def fetch_gen1_data() -> list[dict]:
    """Fetch all 151 Gen 1 Pokémon from PokéAPI. Returns a list of dicts."""
    all_pokemon = []

    for poke_id in range(1, TOTAL_POKEMON + 1):
        print(f"[{poke_id:3d}/{TOTAL_POKEMON}] Fetching...", end=" ", flush=True)

        poke_data = _fetch(f"{BASE_URL}/pokemon/{poke_id}/")
        if not poke_data:
            print("SKIP (no data)")
            continue

        name = poke_data["name"]
        print(name, flush=True)

        stats = {s["stat"]["name"]: s["base_stat"] for s in poke_data.get("stats", [])}
        types = {
            t["slot"]: t["type"]["name"]
            for t in sorted(poke_data.get("types", []), key=lambda x: x["slot"])
        }

        print("    Fetching moves...")
        moves = _get_moves(poke_data)

        species_data: dict = {}
        next_evolutions: list[dict] = []
        if species_url := poke_data.get("species", {}).get("url"):
            print("    Fetching species data...")
            species_data = _fetch(species_url)
            if species_data:
                next_evolutions = _get_next_evolutions(species_data, name)

        print("    Fetching sprite PNGs...")
        front_sprite, back_sprite = _get_sprites(poke_id)

        all_pokemon.append(
            {
                "id": poke_id,
                "name": name,
                "types": types,
                "base_experience": poke_data.get("base_experience"),
                "stats": {
                    "hp": stats.get("hp", 0),
                    "attack": stats.get("attack", 0),
                    "defense": stats.get("defense", 0),
                    "special_attack": stats.get("special-attack", 0),
                    "special_defense": stats.get("special-defense", 0),
                    "speed": stats.get("speed", 0),
                },
                "moves": moves,
                "next_evolutions": next_evolutions,
                "growth_rate": species_data.get("growth_rate", {}).get("name"),
                "front_sprite": front_sprite,
                "back_sprite": back_sprite,
            }
        )

        evo_str = (
            ", ".join(
                f"{e['evolves_into']} (#{e['evolves_into_id']})"
                for e in next_evolutions
            )
            if next_evolutions
            else "none"
        )
        print(f"    → {len(moves)} moves | evo: {evo_str}")

    return all_pokemon


def _upsert_pokemon(cur: sqlite3.Cursor, poke_id: int, poke: dict) -> None:
    stats = poke.get("stats", {})
    types = poke.get("types", {})
    front = poke.get("front_sprite")
    back = poke.get("back_sprite")

    cur.execute(
        """
        INSERT OR REPLACE INTO dex_pokemon
            (id, name, type_1, type_2,
             base_hp, base_attack, base_defense,
             base_sp_attack, base_sp_defense, base_speed,
             base_experience, front_sprite, back_sprite, growth_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            poke_id,
            poke["name"],
            types.get(1, "UNKNOWN"),
            types.get(2),
            stats.get("hp", 0),
            stats.get("attack", 0),
            stats.get("defense", 0),
            stats.get("special_attack", 0),
            stats.get("special_defense", 0),
            stats.get("speed", 0),
            poke.get("base_experience"),
            sqlite3.Binary(front) if front else None,
            sqlite3.Binary(back) if back else None,
            poke.get("growth_rate"),
        ),
    )


def _insert_moves(
    cur: sqlite3.Cursor,
    poke_id: int,
    move_name_to_id: dict[str, int],
    moves: list[dict],
) -> None:
    for move in moves:
        move_name = move["name"]

        if move_name not in move_name_to_id:
            cur.execute(
                """
                INSERT OR IGNORE INTO dex_move
                    (name, power, accuracy, max_pp, type, damage_class,
                     ailment, ailment_chance, move_category, healing, drain)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    move_name,
                    move.get("power"),
                    move.get("accuracy"),
                    move.get("pp") or 1,
                    move.get("type"),
                    move.get("damage_class"),
                    move.get("ailment"),
                    move.get("ailment_chance"),
                    move.get("move_category"),
                    move.get("healing"),
                    move.get("drain"),
                ),
            )
            cur.execute("SELECT id FROM dex_move WHERE name = ?", (move_name,))
            move_name_to_id[move_name] = cur.fetchone()[0]

        cur.execute(
            """
            INSERT OR IGNORE INTO dex_pokemon_moves
                (pokemon_id, move_id, level_learned, learn_method)
            VALUES (?, ?, ?, ?)
            """,
            (
                poke_id,
                move_name_to_id[move_name],
                move.get("level_learned", 0),
                move.get("learn_method", "unknown"),
            ),
        )


def _insert_evolutions(cur: sqlite3.Cursor, evolutions: dict[int, list[tuple]]) -> None:
    for poke_id, evos in evolutions.items():
        for evo in evos:
            try:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO dex_evolutions
                        (pokemon_id, evolves_into_id, trigger, min_level, item, is_player_choice)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (poke_id, *evo),
                )
            except Exception as e:
                print(
                    f"  [WARN] Evolution insert failed (pokemon #{poke_id} → #{evo[0]}): {e}"
                )


def save_to_sqlite(conn: sqlite3.Connection, data: list[dict]) -> None:
    cur = conn.cursor()
    move_name_to_id: dict[str, int] = {}
    evolutions: dict[int, list[tuple]] = {}

    for poke in data:
        poke_id = poke["id"]
        _upsert_pokemon(cur, poke_id, poke)
        _insert_moves(cur, poke_id, move_name_to_id, poke.get("moves", []))

        next_evolutions = poke.get("next_evolutions", [])
        is_player_choice = 1 if len(next_evolutions) > 1 else 0  # Eevee branches

        cur_evos = []
        for evo in next_evolutions:
            if (into_id := evo.get("evolves_into_id")) is None:
                continue
            cur_evos.append(
                (
                    into_id,
                    evo.get("trigger"),
                    evo.get("min_level"),
                    evo.get("item"),
                    is_player_choice,
                )
            )

        if cur_evos:
            evolutions[poke_id] = cur_evos

    _insert_evolutions(cur, evolutions)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM dex_pokemon")
    print(f"  {cur.fetchone()[0]} Pokémon loaded.")
    cur.execute("SELECT COUNT(*) FROM dex_move")
    print(f"  {cur.fetchone()[0]} unique moves loaded.")
    cur.execute("SELECT COUNT(*) FROM dex_evolutions")
    print(f"  {cur.fetchone()[0]} evolution entries loaded.")


def init_db(db_path: Path) -> sqlite3.Connection:
    if not SCHEMA_FILE.exists():
        typer.echo(f"ERROR: schema file not found: {SCHEMA_FILE}", err=True)
        raise typer.Exit(1)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    print(f"  Initialising schema from {SCHEMA_FILE}...")
    with conn:
        conn.executescript(SCHEMA_FILE.read_text())
    return conn


def save_pickle(data: list[dict]) -> None:
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"  Cached {len(data)} Pokémon → {CACHE_FILE}")


def load_pickle() -> list[dict]:
    if not CACHE_FILE.exists():
        typer.echo(f"ERROR: cache file not found: {CACHE_FILE}", err=True)
        raise typer.Exit(1)
    print(f"  Loading cache from {CACHE_FILE}...")
    with open(CACHE_FILE, "rb") as f:
        return pickle.load(f)


app = typer.Typer(
    help=__doc__,
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
)


@app.command()
def main(
    save_cache: Annotated[
        bool,
        typer.Option("--save-cache", help="Save fetched data to local pickle cache."),
    ] = True,
    load_cache: Annotated[
        bool,
        typer.Option(
            "--load-cache",
            help="Load data from pickle cache instead of hitting the API.",
        ),
    ] = False,
    cache_only: Annotated[
        bool,
        typer.Option(
            "--cache-only",
            help="Skip SQLite and exit after saving cache.",
        ),
    ] = False,
) -> None:
    if load_cache and cache_only:
        typer.echo(
            "ERROR: --cache-only and --load-cache are mutually exclusive.", err=True
        )
        raise typer.Exit(1)

    if load_cache:
        typer.echo("Loading from cache...")
        data = load_pickle()
    else:
        typer.echo(f"Fetching {TOTAL_POKEMON} Gen 1 Pokémon from PokéAPI...")
        typer.echo("This will take a while — go grab a coffee ☕\n")
        data = fetch_gen1_data()

    if save_cache or cache_only:
        typer.echo("\nSaving cache...")
        save_pickle(data)
        if cache_only:
            typer.echo("Done! (--cache-only, skipping SQLite)")
            return

    typer.echo(f"\nWriting to {DB_FILE}...")
    with init_db(DB_FILE) as conn:
        save_to_sqlite(conn, data)

    typer.echo("\nAll done! 🎉")


if __name__ == "__main__":
    app()
