#!/usr/bin/env python3
"""
Fetch Gen 1 Pokémon data from PokéAPI for a Red/Blue battle system.

Collects for each of the 151 Pokémon:
  - Base stats (HP, Attack, Defense, Sp.Atk, Sp.Def, Speed)
  - Moves learned in Red/Blue (level-up only, with level learned)
  - Type(s) as [slot, name] pairs
  - Next evolutions (always a list; empty if none, multiple if branching e.g. Eevee)
  - Base experience (XP yielded when defeated)
  - Growth rate name
"""

import pickle
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
import typer

BASE_URL = "https://pokeapi.co/api/v2"
JSON_DATA_FILE = "compiled_gen1_data.json"
PICKLE_DATA_FILE = "pokemon_gen1_data.pkl"
VERSION_GROUP = "red-blue"
TOTAL_POKEMON = 151
DELAY = 0.3  # seconds between requests to be polite

# Trade evolutions don't exist in a single-player context.
# These four are remapped to level-up at level 36 (common fan game standard).
TRADE_EVO_LEVEL = 36

session = requests.Session()


@lru_cache(maxsize=None)
def _fetch(url: str) -> dict:
    """GET with basic error handling. Cached by URL — repeated calls are free."""
    time.sleep(DELAY)
    resp = session.get(url, timeout=10)
    if not resp.ok:
        print(f"Error fetching from api, HTTP Code: {resp.status_code}. {resp.raw}")
        return {}
    return resp.json()


def _get_moves(pokemon_data: dict) -> list[dict]:
    """
    Return moves available in Red/Blue via level-up, with the level learned.
    Each entry: { name, level_learned, power, accuracy, pp, type, damage_class,
                  ailment, ailment_chance, stat_changes, move_category, healing, drain }
    """
    rb_moves = []
    seen = set()

    for move_entry in pokemon_data.get("moves", []):
        for vgd in move_entry.get("version_group_details", []):
            if (
                vgd["version_group"]["name"] == VERSION_GROUP
                # and vgd["move_learn_method"]["name"] == "level-up"
            ):
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
    """
    Build a single evolution entry from a chain node.
    Fetches /pokemon/{name}/ to get the FK-ready pokemon id.
    Remaps trade triggers to level-up at TRADE_EVO_LEVEL.
    """
    next_name = next_node["species"]["name"]
    details = next_node.get("evolution_details", [{}])
    detail = details[0] if details else {}

    trigger = detail.get("trigger", {}).get("name") if detail.get("trigger") else None
    min_level = detail.get("min_level")
    item = detail.get("item", {}).get("name") if detail.get("item") else None

    # Remap trade evolutions to level-up at TRADE_EVO_LEVEL
    if trigger == "trade":
        trigger = "level-up"
        min_level = TRADE_EVO_LEVEL
        item = None

    next_poke_data = _fetch(f"{BASE_URL}/pokemon/{next_name}/")
    next_id = next_poke_data.get("id") if next_poke_data else None

    if not next_id or next_id > TOTAL_POKEMON:
        return None

    return {
        "evolves_into_id": next_id,  # FK-ready pokemon.id
        "evolves_into": next_name,
        "trigger": trigger,
        "min_level": min_level,
        "item": item,
    }


def _get_next_evolutions(species_data: dict, pokemon_name: str) -> list[dict]:
    """
    Walk the evolution chain and return ALL next-stage evolutions for pokemon_name.
    Always returns a list:
      []           — no further evolution (legendaries, final forms, etc.)
      [entry]      — single evolution  (Charmander -> Charmeleon)
      [e1, e2, e3] — branching         (Eevee -> Vaporeon / Jolteon / Flareon)

    Each entry: { evolves_into_id, evolves_into, trigger, min_level, item }
    """
    evo_chain_url = species_data.get("evolution_chain", {}).get("url")
    if not evo_chain_url:
        return []

    chain_data = _fetch(evo_chain_url)
    if not chain_data:
        return []

    def walk(node, target_name):
        if node.get("species", {}).get("name") == target_name:
            evolutions = []
            for child in node.get("evolves_to", []):
                evo_entry = _build_evo_entry(child)
                if not evo_entry:
                    continue
                evolutions.append(evo_entry)
            return evolutions
        for child in node.get("evolves_to", []):
            result = walk(child, target_name)
            if result is not None:
                return result
        return None

    return walk(chain_data.get("chain", {}), pokemon_name) or []


# Will raise a RuntimeError if not an image response
def _check_content_type_is_image(resp) -> None:
    if not resp.ok or not resp.headers["content-type"].startswith("image"):
        raise RuntimeError(
            f"Network request error getting front sprite: {resp.status_code} {resp.raw}"
        )


def _get_sprites(poke_id: int) -> tuple[Any | None, Any | None]:

    if not poke_id:
        raise ValueError("poke_id must have a positive value between 1 - 151.")

    front_png_resp = session.get(
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/{poke_id}.png"
    )
    back_png_resp = session.get(
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/back/{poke_id}.png"
    )
    try:
        _check_content_type_is_image(front_png_resp)
        _check_content_type_is_image(back_png_resp)
    except RuntimeError as e:
        print(e)
        return None, None

    return front_png_resp.content, back_png_resp.content


def fetch_gen1_data() -> list[dict]:
    all_pokemon = []

    for poke_id in range(1, TOTAL_POKEMON + 1):
        print(
            f"[{poke_id:3d}/{TOTAL_POKEMON}] Fetching #{poke_id}...",
            end=" ",
            flush=True,
        )

        poke_data = _fetch(f"{BASE_URL}/pokemon/{poke_id}/")
        if not poke_data:
            print("SKIP (no data)")
            continue

        name = poke_data["name"]
        print(name, flush=True)

        # --- Stats ---
        stats = {s["stat"]["name"]: s["base_stat"] for s in poke_data.get("stats", [])}

        # --- Types ---
        types = {
            t["slot"]: t["type"]["name"]
            for t in sorted(poke_data.get("types", []), key=lambda x: x["slot"])
        }

        # --- Moves (Red/Blue level-up) ---
        print(f"    Fetching moves for {name}...")
        moves = _get_moves(poke_data)

        # --- Species (evolution + growth rate) ---
        species_url = poke_data.get("species", {}).get("url")
        species_data = {}
        next_evolutions = []
        if species_url:
            print(f"    Fetching species data for {name}...")
            species_data = _fetch(species_url)
            if species_data:
                next_evolutions = _get_next_evolutions(species_data, name)
        try:
            front_sprite, back_sprite = _get_sprites(poke_id)
        except Exception as e:
            print(e)
            front_sprite = back_sprite = None

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
                "next_evolutions": next_evolutions,  # [] if none, [e] if one, [e1,e2,...] if branching
                "growth_rate": species_data.get("growth_rate", {}).get("name"),
                "front_sprite": front_sprite,
                "back_sprite": back_sprite,
            }
        )

        if next_evolutions:
            evo_str = ", ".join(
                f"{e['evolves_into']} (id={e['evolves_into_id']})"
                for e in next_evolutions
            )
        else:
            evo_str = "none"
        print(f"    -> {len(moves)} moves | evo: {evo_str}")

    return all_pokemon


def _upsert_pokemon(cur: sqlite3.Cursor, poke_id: int, poke: dict) -> None:
    stats = poke.get("stats", {})

    # types is [[slot, name], ...] — slot 1 always present, slot 2 optional
    types = poke.get("types", {})
    type_1 = types.get(1, "UNKNOWN")
    type_2 = types.get(2)  # None for single-type pokemon
    front_sprite = poke.get("front_sprite")
    back_sprite = poke.get("back_sprite")

    # --- pokemon ---
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
            type_1,
            type_2,
            stats.get("hp", 0),
            stats.get("attack", 0),
            stats.get("defense", 0),
            stats.get("special_attack", 0),
            stats.get("special_defense", 0),
            stats.get("speed", 0),
            poke.get("base_experience"),
            sqlite3.Binary(front_sprite) if front_sprite else None,
            sqlite3.Binary(back_sprite) if back_sprite else None,
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
                    move.get("pp") or 1,  # guard against null pp
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
            INSERT OR IGNORE INTO dex_pokemon_moves (pokemon_id, move_id, level_learned, learn_method)
            VALUES (?, ?, ?, ?)
            """,
            (
                poke_id,
                move_name_to_id[move_name],
                move.get("level_learned", 0),
                move.get("learn_method", "NOT FOUND"),
            ),
        )


def _inserst_evolutions(conn: sqlite3.Connection, evolutions: dict) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    for p_id, evos in evolutions.items():
        if not evos:
            continue
        for evo in evos:
            try:
                cur.execute(
                    """
                        INSERT OR IGNORE INTO dex_evolutions
                            (pokemon_id, evolves_into_id, trigger, min_level, item, is_player_choice)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                    (
                        p_id,
                        evo[0],
                        evo[1],
                        evo[2],
                        evo[3],
                        evo[4],
                    ),
                )
            except Exception as e:
                print(f"Error occurred inserting pokemon_evolutions: {e}")
                print(f"pokemon id: {p_id}, evolves into id: {evo[0]}")

    conn.commit()


def save_to_sqlite(conn: sqlite3.Connection, data: list[dict]) -> None:
    cur = conn.cursor()
    move_name_to_id = {}
    evolutions = {}
    for poke in data:
        poke_id = poke["id"]
        _upsert_pokemon(cur, poke_id, poke)

        # --- moves + pokemon_moves ---
        _insert_moves(cur, poke_id, move_name_to_id, poke.get("moves", []))
        conn.commit()

        # --- pokemon_evolutions ---
        # need to insert ALL pokemon first, then pokemon_evolutions
        next_evolutions = poke.get("next_evolutions", [])
        is_player_choice = 1 if len(next_evolutions) > 1 else 0  # eevee evos ...

        cur_evos = []

        for evo in next_evolutions:
            into_id = evo.get("evolves_into_id")
            if into_id is None:
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

    _inserst_evolutions(conn, evolutions)

    cur.execute("SELECT COUNT(*) FROM dex_pokemon")
    print(f"  Loaded {cur.fetchone()[0]} Pokémon.")

    cur.execute("SELECT COUNT(*) FROM dex_move")
    print(f"  Loaded {cur.fetchone()[0]} unique moves.")

    cur.execute("SELECT COUNT(*) FROM dex_evolutions")
    print(f"  Loaded {cur.fetchone()[0]} evolution entries.")


def main(
    fetch_only: bool = False,
    save_ir: bool = False,
    load_data_file: bool = False,
):
    if load_data_file:
        # print(f"Loading data from {JSON_DATA_FILE}")
        # with open(JSON_DATA_FILE) as f:
        #     data = json.load(f)
        # for item in data:
        #     if fsp := item.get("front_sprite"):
        #         item["front_sprite"] = base64.b64decode(fsp)
        #     if bsp := item.get("back_sprite"):
        #         item["back_sprite"] = base64.b64decode(bsp)
        print(f"Loading data from {PICKLE_DATA_FILE}")
        with open(PICKLE_DATA_FILE, "rb") as f:
            data = pickle.load(f)

    else:
        print(f"Fetching data for {TOTAL_POKEMON} Gen 1 Pokémon (Red/Blue only)...")
        print("This will take a while due to rate limiting. Go grab a coffee ☕\n")
        # this will do all the network requests
        data = fetch_gen1_data()

    if fetch_only or save_ir:
        # # encode png data when saving to json file
        # for item in data:
        #     if fsp := item.get("front_sprite"):
        #         item["front_sprite"] = base64.b64encode(fsp).decode()
        #     if bsp := item.get("back_sprite"):
        #         item["back_sprite"] = base64.b64encode(bsp).decode()

        # with open(DATA_FILE, "w") as f:
        #     json.dump(data, f, indent=2)
        # print(f"\nDone! Saved {len(data)} Pokémon to {JSON_DATA_FILE}")
        with open(PICKLE_DATA_FILE, "wb") as f:
            pickle.dump(data, f)

        if fetch_only:
            print(f"\nDone! Saved {len(data)} Pokémon to {PICKLE_DATA_FILE}")
            return

    # this will save all data to sqlite
    db_path = Path("pokedata.db")

    with open("POKEMON_TABLE_SCHEMAS.sql") as f:
        sql_scripts = f.read()

    conn = sqlite3.connect(db_path)
    try:
        print("Creating Table schema...")
        cur = conn.cursor()
        # cur.execute("PRAGMA foreign_keys = ON")
        cur.executescript(sql_scripts)
        conn.commit()

        save_to_sqlite(conn, data)
    finally:
        conn.close()

    print("\nAll done! Database is ready.")


if __name__ == "__main__":
    typer.run(main)
