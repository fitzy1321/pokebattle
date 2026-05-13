"""
Fetch Gen 1 Pokémon data from PokéAPI for a Red/Blue battle system.

Collects for each of the 151 Pokémon:
  - Base stats (HP, Attack, Defense, Sp.Atk, Sp.Def, Speed)
  - Moves learned in Red/Blue (level-up only, with level learned)
  - Type(s) as [slot, name] pairs
  - Next evolution (if any) and the level/trigger for it
  - Base experience (XP yielded when defeated)
  - Growth rate XP table (XP required per level)
"""

import json
import time

import requests

BASE_URL = "https://pokeapi.co/api/v2"
OUTPUT_FILE = "compiled_pokemon_data.json"
VERSION_GROUP = "red-blue"
TOTAL_POKEMON = 151
DELAY = 0.3  # seconds between requests to be polite

session = requests.Session()


def get(url: str) -> dict:
    """Simple GET with basic error handling."""
    resp = session.get(url, timeout=10)
    if not resp.ok:
        print(f"Error fetching from api, HTTP Code: {resp.status_code}. {resp.raw}")
        return {}

    return resp.json()


def get_moves(pokemon_data: dict) -> list[dict]:
    """
    Return moves available in Red/Blue via level-up, with the level learned.
    Each entry: { name, level, power, accuracy, pp, type, damage_class }
    We fetch move details for each unique move used in red-blue.
    """
    rb_moves = []
    seen = set()

    for move_entry in pokemon_data.get("moves", []):
        for vgd in move_entry.get("version_group_details", []):
            if (
                vgd["version_group"]["name"] == VERSION_GROUP
                and vgd["move_learn_method"]["name"] == "level-up"
            ):
                move_name = move_entry["move"]["name"]
                if move_name not in seen:
                    seen.add(move_name)
                    rb_moves.append(
                        {
                            "name": move_name,
                            "level": vgd["level_learned_at"],
                            "url": move_entry["move"]["url"],
                        }
                    )

    # Sort by level learned
    rb_moves.sort(key=lambda m: m["level"])

    # Fetch details for each move
    detailed = []
    for m in rb_moves:
        time.sleep(DELAY)
        data = get(m["url"])
        if not data:
            continue
        meta = data.get("meta") or {}
        detailed.append(
            {
                "name": m["name"],
                "level_learned": m["level"],
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


def get_next_evolution(species_data: dict, pokemon_name: str) -> dict | None:
    """
    Walk the evolution chain and return the next stage after pokemon_name.
    Returns { evolves_into, trigger, min_level } or None.
    """
    evo_chain_url = species_data.get("evolution_chain", {}).get("url")
    if not evo_chain_url:
        return None

    time.sleep(DELAY)
    chain_data = get(evo_chain_url)
    if not chain_data:
        return None

    # Walk the chain tree looking for our pokemon, then return what it evolves into
    def walk(node, target_name):
        species_name = node.get("species", {}).get("name", "")
        if species_name == target_name:
            # Found it — return first evolution if any
            evolutions = node.get("evolves_to", [])
            if evolutions:
                next_node = evolutions[0]
                next_name = next_node["species"]["name"]
                details = next_node.get("evolution_details", [{}])
                detail = details[0] if details else {}
                return {
                    "evolves_into": next_name,
                    "trigger": detail.get("trigger", {}).get("name")
                    if detail.get("trigger")
                    else None,
                    "min_level": detail.get("min_level"),
                    "item": detail.get("item", {}).get("name")
                    if detail.get("item")
                    else None,
                }
            return None  # No further evolution

        # Recurse into branches
        for child in node.get("evolves_to", []):
            result = walk(child, target_name)
            if result is not None:
                return result
        return None

    return walk(chain_data.get("chain", {}), pokemon_name)


def get_growth_rate_table(species_data: dict) -> list[dict]:
    """
    Returns the XP-per-level table for this pokemon's growth rate.
    Each entry: { level, experience }
    """
    growth_rate_url = species_data.get("growth_rate", {}).get("url")
    if not growth_rate_url:
        return []

    time.sleep(DELAY)
    gr_data = get(growth_rate_url)
    if not gr_data:
        return []

    return [
        {"level": e["level"], "experience": e["experience"]}
        for e in gr_data.get("levels", [])
    ]


def fetch_all():
    all_pokemon = []

    for poke_id in range(1, TOTAL_POKEMON + 1):
        print(
            f"[{poke_id:3d}/{TOTAL_POKEMON}] Fetching #{poke_id}...",
            end=" ",
            flush=True,
        )

        time.sleep(DELAY)
        poke_data = get(f"{BASE_URL}/pokemon/{poke_id}/")
        if not poke_data:
            print("SKIP (no data)")
            continue

        name = poke_data["name"]
        print(name, flush=True)

        # --- Stats ---
        stats = {s["stat"]["name"]: s["base_stat"] for s in poke_data.get("stats", [])}

        # --- Types ---
        types = [
            [t["slot"], t["type"]["name"]]
            for t in sorted(poke_data.get("types", []), key=lambda x: x["slot"])
        ]

        # --- Moves (Red/Blue level-up) ---
        print(f"    Fetching moves for {name}...")
        moves = get_moves(poke_data)

        # --- Evolution & Growth Rate (fetch species once, share it) ---
        species_url = poke_data.get("species", {}).get("url")
        next_evo = None
        xp_table = []
        if species_url:
            print(f"    Fetching species data for {name}...")
            time.sleep(DELAY)
            species_data = get(species_url)
            if species_data:
                next_evo = get_next_evolution(species_data, name)
                xp_table = get_growth_rate_table(species_data)

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
                "next_evolution": next_evo,
                "xp_table": xp_table,
            }
        )

        print(
            f"    -> {len(moves)} moves | evo: {next_evo['evolves_into'] if next_evo else 'none'}"
        )

    return all_pokemon


if __name__ == "__main__":
    print(f"Fetching data for {TOTAL_POKEMON} Gen 1 Pokémon (Red/Blue only)...")
    print("This will take a while due to rate limiting. Go grab a coffee ☕\n")

    data = fetch_all()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone! Saved {len(data)} Pokémon to {OUTPUT_FILE}")
