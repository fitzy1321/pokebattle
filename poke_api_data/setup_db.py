#!/usr/bin/env python3
import json
import os
import sqlite3
from pathlib import Path

STATIC_TABLES_SCHEMA = """
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
    growth_rate     TEXT                   -- e.g. "slow", "medium-slow", "medium-fast" "fast"
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
    pokemon_id    INTEGER NOT NULL,       -- FK pokemon(id)
    move_id       INTEGER NOT NULL,       -- FK moves(id)
    level_learned INTEGER NOT NULL,       -- 0 = learned at start
    FOREIGN KEY(pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY(move_id) REFERENCES moves(id),
    UNIQUE(pokemon_id, move_id)
);

CREATE TABLE IF NOT EXISTS pokemon_evolutions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id       INTEGER NOT NULL REFERENCES pokemon(id),  -- who evolves
    evolves_into_id  INTEGER NOT NULL REFERENCES pokemon(id),  -- what it becomes
    trigger          TEXT,                                     -- "level-up" | "use-item" | NULL
    min_level        INTEGER,                                  -- NULL for stone evolutions
    item             TEXT,                                     -- e.g. "fire-stone", NULL otherwise
    is_player_choice INTEGER NOT NULL DEFAULT 0,               -- 1 = player must pick (Eevee's 3 branches)
    FOREIGN KEY(pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY(evolves_into_id) REFERENCES pokemon(id),
    UNIQUE(pokemon_id, evolves_into_id)
);
"""

# -- The player's current party (up to 6 pokemon)
# CREATE TABLE IF NOT EXISTS party_pokemon (
#     id         INTEGER PRIMARY KEY AUTOINCREMENT,
#     pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
#     nickname   TEXT,                     -- NULL = use species name in C
#     level      INTEGER NOT NULL DEFAULT 5,
#     xp         INTEGER NOT NULL DEFAULT 0,
#     max_hp     INTEGER NOT NULL,         -- recalculated on level-up
#     current_hp INTEGER NOT NULL,         -- set to max_hp on heal
#     party_slot INTEGER NOT NULL UNIQUE   -- 1-6, enforces party order
# );

# -- The 4 moves each party member currently knows
# CREATE TABLE IF NOT EXISTS party_pokemon_moves (
#     id               INTEGER PRIMARY KEY AUTOINCREMENT,
#     party_pokemon_id INTEGER NOT NULL REFERENCES party_pokemon(id) ON DELETE CASCADE,
#     move_id          INTEGER NOT NULL REFERENCES moves(id),
#     slot             INTEGER NOT NULL,   -- 1-4, move order
#     current_pp       INTEGER NOT NULL,   -- set to moves.max_pp on heal
#     UNIQUE(party_pokemon_id, slot)
# );

# -- Current enemy pokemon — enforced single row via CHECK (id = 1)
# CREATE TABLE IF NOT EXISTS enemy_pokemon (
#     id         INTEGER PRIMARY KEY CHECK (id = 1),
#     pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
#     level      INTEGER NOT NULL DEFAULT 5,
#     current_hp INTEGER NOT NULL,
#     max_hp     INTEGER NOT NULL
# );


def upsert_pokemon(cur: sqlite3.Cursor, poke_id: int, poke: dict) -> None:
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


def insert_moves(
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


def inserst_evolutions(conn: sqlite3.Connection, evolutions: dict) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    for p_id, evos in evolutions.items():
        if not evos:
            continue
        for evo in evos:
            try:
                cur.execute(
                    """
                        INSERT OR IGNORE INTO pokemon_evolutions
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


def load_static_data(conn: sqlite3.Connection, data: list[dict]) -> None:
    cur = conn.cursor()
    move_name_to_id = {}
    evolutions = {}
    for poke in data:
        poke_id = poke["id"]
        upsert_pokemon(cur, poke_id, poke)

        # --- moves + pokemon_moves ---
        insert_moves(cur, poke_id, move_name_to_id, poke.get("moves", []))
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

    inserst_evolutions(conn, evolutions)

    cur.execute("SELECT COUNT(*) FROM pokemon")
    print(f"  Loaded {cur.fetchone()[0]} Pokémon.")
    cur.execute("SELECT COUNT(*) FROM moves")
    print(f"  Loaded {cur.fetchone()[0]} unique moves.")
    cur.execute("SELECT COUNT(*) FROM pokemon_evolutions")
    print(f"  Loaded {cur.fetchone()[0]} evolution entries.")


def main():
    FILE_NAME = "compiled_pokemon_data.json"
    cwd = Path(os.getcwd())
    data_path = cwd / FILE_NAME
    if not data_path.exists():
        data_path = cwd / "poke_api_data" / FILE_NAME
    if not data_path.exists():
        print(f"ERROR: data file not found: {data_path}")
        raise SystemExit(1)

    print(f"Data file: {data_path}")

    db_path = Path("pokedata.db")
    if db_path.exists():
        os.remove(db_path)

    print(f"Database : {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        # # if args.reset:
        # print("Dropping all tables...")
        # stmt = "; ".join(
        #     [
        #         f"DROP TABLE IF EXISTS {table}"
        #         for table in ["pokemon", "moves", "pokemon_moves", "pokemon_evolutions"]
        #     ]
        # )
        # conn.executescript(stmt)
        # conn.commit()
        # print("Done.")

        print("Creating schema...")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(STATIC_TABLES_SCHEMA)
        conn.commit()

        print("Loading static Pokémon data...")
        with open(data_path) as f:
            data = json.load(f)
        load_static_data(conn, data)
    finally:
        conn.close()

    print("\nAll done! Database is ready.")


if __name__ == "__main__":
    main()
