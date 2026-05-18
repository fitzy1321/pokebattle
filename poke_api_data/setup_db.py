#!/usr/bin/env python3
"""
setup_db.py

Creates the SQLite database schema and loads all static Pokémon data
from compiled_pokemon_data.json produced by compile_gen1_data.py.

Static tables (read-only at runtime):
  pokemon            — base stats, types (flat type_1/type_2), growth rate, base experience
  moves              — deduplicated move definitions
  pokemon_moves      — learnable moves per pokemon with level
  pokemon_evolutions — next evolution(s) per pokemon; is_player_choice=1 for Eevee

Instance tables (mutable game state):
  party_pokemon       — player's party (up to 6), level/xp/hp per member
  party_pokemon_moves — up to 4 moves per party member, with current PP
  enemy_pokemon       — single-row current enemy, replaced each encounter

Usage:
  python setup_db.py                              # uses compiled_pokemon_data.json + pokemon.db
  python setup_db.py --data my_data.json          # custom data file
  python setup_db.py --db my_game.db              # custom db path
  python setup_db.py --reset                      # drop and recreate everything
"""

import json
import os
import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------------------
-- Static / Pokédex tables
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pokemon (
    id              INTEGER PRIMARY KEY,   -- matches PokéAPI pokemon id
    name            TEXT    NOT NULL UNIQUE,
    type_1          TEXT    NOT NULL,      -- primary type, always present
    type_2          TEXT,                  -- secondary type, NULL if single-type
    base_hp         INTEGER NOT NULL,
    base_attack     INTEGER NOT NULL,
    base_defense    INTEGER NOT NULL,
    base_sp_attack  INTEGER NOT NULL,
    base_sp_defense INTEGER NOT NULL,
    base_speed      INTEGER NOT NULL,
    base_experience INTEGER,               -- XP yielded when defeated
    growth_rate     TEXT                   -- e.g. "medium-slow"
);

CREATE TABLE IF NOT EXISTS moves (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    power          INTEGER,               -- NULL for status moves
    accuracy       INTEGER,               -- NULL for moves that never miss
    max_pp         INTEGER NOT NULL,      -- base PP; current PP tracked in party_pokemon_moves
    type           TEXT,
    damage_class   TEXT,                  -- "physical" | "special" | "status"
    ailment        TEXT,                  -- e.g. "paralysis", "poison", NULL if none
    ailment_chance INTEGER,
    move_category  TEXT,                  -- PokéAPI meta category e.g. "damage+ailment"
    healing        INTEGER,               -- % HP restored, NULL if none
    drain          INTEGER                -- % HP drained from target, NULL if none
);

CREATE TABLE IF NOT EXISTS pokemon_moves (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id    INTEGER NOT NULL REFERENCES pokemon(id),
    move_id       INTEGER NOT NULL REFERENCES moves(id),
    level_learned INTEGER NOT NULL,       -- 0 = learned at start
    UNIQUE(pokemon_id, move_id)
);

CREATE TABLE IF NOT EXISTS pokemon_evolutions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id       INTEGER NOT NULL REFERENCES pokemon(id),  -- who evolves
    evolves_into_id  INTEGER NOT NULL REFERENCES pokemon(id),  -- what it becomes
    trigger          TEXT,               -- "level-up" | "use-item" | NULL
    min_level        INTEGER,            -- NULL for stone evolutions
    item             TEXT,               -- e.g. "fire-stone", NULL otherwise
    is_player_choice INTEGER NOT NULL DEFAULT 0  -- 1 = player must pick (Eevee's 3 branches)
);

-- -------------------------------------------------------------------------
-- Instance / game state tables
-- -------------------------------------------------------------------------

-- The player's current party (up to 6 pokemon)
CREATE TABLE IF NOT EXISTS party_pokemon (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
    nickname   TEXT,                     -- NULL = use species name in C
    level      INTEGER NOT NULL DEFAULT 5,
    xp         INTEGER NOT NULL DEFAULT 0,
    max_hp     INTEGER NOT NULL,         -- recalculated on level-up
    current_hp INTEGER NOT NULL,         -- set to max_hp on heal
    party_slot INTEGER NOT NULL UNIQUE   -- 1-6, enforces party order
);

-- The 4 moves each party member currently knows
CREATE TABLE IF NOT EXISTS party_pokemon_moves (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    party_pokemon_id INTEGER NOT NULL REFERENCES party_pokemon(id) ON DELETE CASCADE,
    move_id          INTEGER NOT NULL REFERENCES moves(id),
    slot             INTEGER NOT NULL,   -- 1-4, move order
    current_pp       INTEGER NOT NULL,   -- set to moves.max_pp on heal
    UNIQUE(party_pokemon_id, slot)
);

-- Current enemy pokemon — enforced single row via CHECK (id = 1)
CREATE TABLE IF NOT EXISTS enemy_pokemon (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
    level      INTEGER NOT NULL DEFAULT 5,
    current_hp INTEGER NOT NULL,
    max_hp     INTEGER NOT NULL
);
"""

# ---------------------------------------------------------------------------
# HP formula
# ---------------------------------------------------------------------------


def calc_max_hp(base_hp: int, level: int) -> int:
    """
    Simplified Gen 1 HP formula with zeroed IVs/EVs:
        floor((2 * base_hp * level) / 100) + level + 10
    """
    return (2 * base_hp * level) // 100 + level + 10


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_static_data(conn: sqlite3.Connection, data: list[dict]) -> None:
    cur = conn.cursor()
    move_name_to_id: dict[str, int] = {}

    for poke in data:
        poke_id = poke["id"]
        stats = poke.get("stats", {})

        # types is [[slot, name], ...] — slot 1 always present, slot 2 optional
        types = {slot: name for slot, name in poke.get("types", [])}
        type_1 = types.get(1)
        type_2 = types.get(2)  # None for single-type pokemon

        # --- pokemon ---
        cur.execute(
            """
            INSERT OR REPLACE INTO pokemon
                (id, name, type_1, type_2,
                 base_hp, base_attack, base_defense,
                 base_sp_attack, base_sp_defense, base_speed,
                 base_experience, growth_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                poke.get("growth_rate"),
            ),
        )

        # --- moves + pokemon_moves ---
        for move in poke.get("moves", []):
            move_name = move["name"]

            if move_name not in move_name_to_id:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO moves
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
                cur.execute("SELECT id FROM moves WHERE name = ?", (move_name,))
                move_name_to_id[move_name] = cur.fetchone()[0]

            cur.execute(
                """
                INSERT OR IGNORE INTO pokemon_moves (pokemon_id, move_id, level_learned)
                VALUES (?, ?, ?)
                """,
                (poke_id, move_name_to_id[move_name], move.get("level_learned", 0)),
            )

        # --- pokemon_evolutions ---
        next_evolutions = poke.get("next_evolutions", [])
        is_player_choice = 1 if len(next_evolutions) > 1 else 0

        for evo in next_evolutions:
            if evo.get("evolves_into_id") is None:
                continue
            cur.execute(
                """
                INSERT OR IGNORE INTO pokemon_evolutions
                    (pokemon_id, evolves_into_id, trigger, min_level, item, is_player_choice)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    poke_id,
                    evo["evolves_into_id"],
                    evo.get("trigger"),
                    evo.get("min_level"),
                    evo.get("item"),
                    is_player_choice,
                ),
            )

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM pokemon")
    print(f"  Loaded {cur.fetchone()[0]} Pokémon.")
    cur.execute("SELECT COUNT(*) FROM moves")
    print(f"  Loaded {cur.fetchone()[0]} unique moves.")
    cur.execute("SELECT COUNT(*) FROM pokemon_evolutions")
    print(f"  Loaded {cur.fetchone()[0]} evolution entries.")


# ---------------------------------------------------------------------------
# Party / enemy helpers
# ---------------------------------------------------------------------------


def add_party_pokemon(
    conn: sqlite3.Connection,
    pokemon_id: int,
    level: int = 5,
    slot: int = 1,
    nickname: str | None = None,
) -> int | None:
    """
    Add a pokemon to the player's party.
    Calculates max_hp, sets current_hp = max_hp.
    Assigns the 4 most recently learnable moves at or below the given level.
    Returns the new party_pokemon.id.
    """
    cur = conn.cursor()

    cur.execute("SELECT base_hp FROM pokemon WHERE id = ?", (pokemon_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"No pokemon with id={pokemon_id}")

    max_hp = calc_max_hp(row[0], level)

    cur.execute(
        """
        INSERT INTO party_pokemon (pokemon_id, nickname, level, xp, max_hp, current_hp, party_slot)
        VALUES (?, ?, ?, 0, ?, ?, ?)
        """,
        (pokemon_id, nickname, level, max_hp, max_hp, slot),
    )
    party_id = cur.lastrowid

    # Best 4 moves learnable at or below current level (highest level first)
    cur.execute(
        """
        SELECT m.id, m.max_pp
        FROM pokemon_moves pm
        JOIN moves m ON m.id = pm.move_id
        WHERE pm.pokemon_id = ? AND pm.level_learned <= ?
        ORDER BY pm.level_learned DESC
        LIMIT 4
        """,
        (pokemon_id, level),
    )
    for move_slot, (move_id, max_pp) in enumerate(cur.fetchall(), start=1):
        cur.execute(
            """
            INSERT INTO party_pokemon_moves (party_pokemon_id, move_id, slot, current_pp)
            VALUES (?, ?, ?, ?)
            """,
            (party_id, move_id, move_slot, max_pp),
        )

    conn.commit()
    return party_id


def set_enemy_pokemon(
    conn: sqlite3.Connection,
    pokemon_id: int,
    level: int = 5,
) -> None:
    """
    Set (or replace) the current enemy pokemon.
    Always a single row (id=1) in enemy_pokemon.
    """
    cur = conn.cursor()

    cur.execute("SELECT base_hp FROM pokemon WHERE id = ?", (pokemon_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"No pokemon with id={pokemon_id}")

    max_hp = calc_max_hp(row[0], level)

    cur.execute(
        """
        INSERT INTO enemy_pokemon (id, pokemon_id, level, current_hp, max_hp)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            pokemon_id = excluded.pokemon_id,
            level      = excluded.level,
            current_hp = excluded.current_hp,
            max_hp     = excluded.max_hp
        """,
        (pokemon_id, level, max_hp, max_hp),
    )
    conn.commit()


def set_random_enemy(
    conn: sqlite3.Connection,
    level: int = 5,
    type_filter: str | None = None,
) -> dict:
    """
    Pick a random pokemon from the pokedex and set it as the enemy.
    Optionally filter by type (matches type_1 OR type_2).
    Returns { id, name, level }.
    """
    cur = conn.cursor()

    if type_filter:
        cur.execute(
            """
            SELECT id, name FROM pokemon
            WHERE type_1 = ? OR type_2 = ?
            ORDER BY RANDOM() LIMIT 1
            """,
            (type_filter, type_filter),
        )
    else:
        cur.execute("SELECT id, name FROM pokemon ORDER BY RANDOM() LIMIT 1")

    row = cur.fetchone()
    if not row:
        raise ValueError(f"No pokemon found matching type_filter={type_filter!r}")

    set_enemy_pokemon(conn, row[0], level)
    return {"id": row[0], "name": row[1], "level": level}


def heal_party(conn: sqlite3.Connection) -> None:
    """
    Fully heal all party pokemon.
    Sets current_hp = max_hp and current_pp = moves.max_pp.
    """
    cur = conn.cursor()
    cur.execute("UPDATE party_pokemon SET current_hp = max_hp")
    cur.execute(
        """
        UPDATE party_pokemon_moves
        SET current_pp = (
            SELECT max_pp FROM moves WHERE moves.id = party_pokemon_moves.move_id
        )
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    # parser = argparse.ArgumentParser(description="Set up the Pokémon SQLite database.")
    # parser.add_argument(
    #     "--data", default="compiled_pokemon_data.json", help="Path to JSON data file"
    # )
    # parser.add_argument("--db", default="pokedata.db", help="Path to SQLite database")
    # parser.add_argument(
    #     "--reset", action="store_true", help="Drop and recreate all tables"
    # )
    # args = parser.parse_args()

    # db_path = Path(args.db)
    # data_path = Path(args.data)
    db_path = Path("pokedata.db")
    data_path = Path(os.getcwd())
    if "poke_api_data" not in data_path.parts:
        data_path = data_path / "poke_api_data"
    data_path = data_path / "compiled_pokemon_data.db"
    if not data_path.exists():
        print(f"ERROR: data file not found: {data_path}")
        return

    print(f"Database : {db_path}")
    print(f"Data file: {data_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # if args.reset:
    print("Dropping all tables...")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (table,) in cur.fetchall():
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    print("Done.")

    print("Creating schema...")
    conn.executescript(SCHEMA)
    conn.commit()

    print("Loading static Pokémon data...")
    with open(data_path) as f:
        data = json.load(f)
    load_static_data(conn, data)

    print("\nAll done! Database is ready.")
    print("\nQuick-start example:")
    print("  from setup_db import add_party_pokemon, set_random_enemy, heal_party")
    print("  conn = sqlite3.connect('pokemon.db')")
    print("  add_party_pokemon(conn, pokemon_id=4, level=10, slot=1)  # Charmander")
    print("  set_random_enemy(conn, level=8)")
    print("  set_random_enemy(conn, level=8, type_filter='fire')")
    print("  heal_party(conn)")

    conn.close()


if __name__ == "__main__":
    main()
