#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DATA_DIR = "data"
DATA_FILE_NAME = "compiled_pokemon_data.json"
SCHEMA_FILE_NAME = "POKEMON_TABLE_SCHEMAS.sql"


def upsert_pokemon(cur: sqlite3.Cursor, poke_id: int, poke: dict) -> None:
    stats = poke.get("stats", {})

    # types is [[slot, name], ...] — slot 1 always present, slot 2 optional
    types = poke.get("types", {})
    type_1 = types.get(1, "UNKNOWN")
    type_2 = types.get(2)  # None for single-type pokemon

    # --- pokemon ---
    cur.execute(
        """
        INSERT OR REPLACE INTO dex_pokemon
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

    cur.execute("SELECT COUNT(*) FROM dex_pokemon")
    print(f"  Loaded {cur.fetchone()[0]} Pokémon.")

    cur.execute("SELECT COUNT(*) FROM dex_move")
    print(f"  Loaded {cur.fetchone()[0]} unique moves.")

    cur.execute("SELECT COUNT(*) FROM dex_evolutions")
    print(f"  Loaded {cur.fetchone()[0]} evolution entries.")


def find_file(p: Path, file_name: str) -> Path | None:
    if p.is_file() and file_name in p.parts:
        return p

    for sp in [p, *p.parents]:
        candidate = sp / file_name
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def main():
    cwd = Path.cwd()

    data_file_path = find_file(cwd / DATA_DIR / DATA_FILE_NAME, DATA_FILE_NAME)
    if not data_file_path or not data_file_path.exists():
        print(f"ERROR: data file not found: {DATA_FILE_NAME}")
        raise SystemExit(1)

    sql_file_path = find_file(cwd / DATA_DIR / SCHEMA_FILE_NAME, SCHEMA_FILE_NAME)
    if not sql_file_path or not sql_file_path.exists():
        print(f"ERROR: sql schema file not found: {SCHEMA_FILE_NAME}")
        raise SystemExit(1)

    db_path = Path("pokedata.db")
    print(f"Data file: {data_file_path}")
    print(f"Database : {db_path}")
    print(f"SQL Schema file: {sql_file_path}")

    with open(sql_file_path) as f:
        sql_scripts = f.read()

    conn = sqlite3.connect(db_path)
    try:
        print("Creating Table schema...")
        cur = conn.cursor()
        # cur.execute("PRAGMA foreign_keys = ON")
        cur.executescript(sql_scripts)
        conn.commit()

        print("Loading static Pokémon data...")
        # large file, will take a bit
        with open(data_file_path) as f:
            data = json.load(f)
        load_static_data(conn, data)
    finally:
        conn.close()

    print("\nAll done! Database is ready.")


if __name__ == "__main__":
    main()
