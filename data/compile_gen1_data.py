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

import base64
import json
import time
from functools import lru_cache

import requests

BASE_URL = "https://pokeapi.co/api/v2"
OUTPUT_FILE = "data/compiled_gen1_data.json"
VERSION_GROUP = "red-blue"
TOTAL_POKEMON = 151
DELAY = 0.3  # seconds between requests to be polite

# Trade evolutions don't exist in a single-player context.
# These four are remapped to level-up at level 36 (common fan game standard).
TRADE_EVO_LEVEL = 36

session = requests.Session()


@lru_cache(maxsize=None)
def fetch(url: str) -> dict:
    """GET with basic error handling. Cached by URL — repeated calls are free."""
    time.sleep(DELAY)
    resp = session.get(url, timeout=10)
    if not resp.ok:
        print(f"Error fetching from api, HTTP Code: {resp.status_code}. {resp.raw}")
        return {}
    return resp.json()


def get_moves(pokemon_data: dict) -> list[dict]:
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
        data = fetch(m["url"])
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


def build_evo_entry(next_node: dict) -> dict | None:
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

    next_poke_data = fetch(f"{BASE_URL}/pokemon/{next_name}/")
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


def get_next_evolutions(species_data: dict, pokemon_name: str) -> list[dict]:
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

    chain_data = fetch(evo_chain_url)
    if not chain_data:
        return []

    def walk(node, target_name):
        if node.get("species", {}).get("name") == target_name:
            evolutions = []
            for child in node.get("evolves_to", []):
                evo_entry = build_evo_entry(child)
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


def get_sprites(poke_id: int) -> tuple[str | None, str | None]:
    def _check_content_type(resp):
        if not resp.ok or not resp.headers["content-type"].startswith("image"):
            raise RuntimeError(
                f"Network request error getting front sprite: {resp.status_code} {resp.raw}"
            )

    if not poke_id:
        raise ValueError("poke_id must have a positive value between 1 - 151.")

    front_png_resp = session.get(
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/{poke_id}.png"
    )
    back_png_resp = session.get(
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/transparent/back/{poke_id}.png"
    )
    try:
        _check_content_type(front_png_resp)
        _check_content_type(back_png_resp)
    except RuntimeError as e:
        print(e)
        return None, None
    front_sprite = base64.b64encode(front_png_resp.content).decode()
    back_sprite = base64.b64encode(back_png_resp.content).decode()
    return front_sprite, back_sprite


def fetch_all():
    all_pokemon = []

    for poke_id in range(1, TOTAL_POKEMON + 1):
        print(
            f"[{poke_id:3d}/{TOTAL_POKEMON}] Fetching #{poke_id}...",
            end=" ",
            flush=True,
        )

        poke_data = fetch(f"{BASE_URL}/pokemon/{poke_id}/")
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
        moves = get_moves(poke_data)

        # --- Species (evolution + growth rate) ---
        species_url = poke_data.get("species", {}).get("url")
        species_data = {}
        next_evolutions = []
        if species_url:
            print(f"    Fetching species data for {name}...")
            species_data = fetch(species_url)
            if species_data:
                next_evolutions = get_next_evolutions(species_data, name)
        try:
            front_sprite, back_sprite = get_sprites(poke_id)
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


def main():
    print(f"Fetching data for {TOTAL_POKEMON} Gen 1 Pokémon (Red/Blue only)...")
    print("This will take a while due to rate limiting. Go grab a coffee ☕\n")

    data = fetch_all()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone! Saved {len(data)} Pokémon to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
