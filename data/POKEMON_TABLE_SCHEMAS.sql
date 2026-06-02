DROP TABLE IF EXISTS dex_pokemon;
CREATE TABLE dex_pokemon (
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

DROP TABLE IF EXISTS dex_move;
CREATE TABLE dex_move (
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

DROP TABLE IF EXISTS dex_pokemon_moves;
CREATE TABLE dex_pokemon_moves (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id    INTEGER NOT NULL,       -- FK pokemon(id)
    move_id       INTEGER NOT NULL,       -- FK moves(id)
    level_learned INTEGER NOT NULL,       -- 0 = learned at start
    learn_method  TEXT,
    FOREIGN KEY(pokemon_id) REFERENCES dex_pokemon(id),
    FOREIGN KEY(move_id) REFERENCES dex_move(id),
    UNIQUE(pokemon_id, move_id)
);

DROP TABLE IF EXISTS dex_evolutions;
CREATE TABLE dex_evolutions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id       INTEGER NOT NULL,  -- who evolves
    evolves_into_id  INTEGER NOT NULL,  -- what it becomes
    trigger          TEXT,                                     -- "level-up" | "use-item" | NULL
    min_level        INTEGER,                                  -- NULL for stone evolutions
    item             TEXT,                                     -- e.g. "fire-stone", NULL otherwise
    is_player_choice INTEGER NOT NULL DEFAULT 0,               -- 1 = player must pick (Eevee's 3 branches)
    FOREIGN KEY(pokemon_id) REFERENCES dex_pokemon(id),
    FOREIGN KEY(evolves_into_id) REFERENCES dex_pokemon(id),
    UNIQUE(pokemon_id, evolves_into_id)
);


DROP TABLE IF EXISTS user_save;
CREATE TABLE user_save (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL
);

DROP TABLE IF EXISTS user_party_pokemon;
CREATE TABLE user_party_pokemon (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_save_id        INTEGER NOT NULL, -- FK
    pokemon_id          INTEGER NOT NULL, -- FK
    display_name        TEXT, -- nickname
    party_order_num     INTEGER NOT NULL, -- 1 - 6
    curr_health         INTEGER NOT NULL,
    max_health          INTEGER NOT NULL,
    move_1_id           INTEGER NOT NULL, -- FK
    move_1_pp           INTEGER NOT NULL,
    move_2_id           INTEGER NOT NULL, -- FK
    move_2_pp           INTEGER NOT NULL,
    move_3_id           INTEGER NOT NULL, -- FK
    move_3_pp           INTEGER NOT NULL,
    move_4_id           INTEGER NOT NULL, --FK
    move_4_pp           INTEGER NOT NULL,
    -- ailments?
    -- status effects?
    FOREIGN KEY(user_save_id) REFERENCES user_save(id),
    FOREIGN KEY(pokemon_id) REFERENCES dex_pokemon(id),
    FOREIGN KEY(move_1_id) REFERENCES dex_move(id),
    FOREIGN KEY(move_2_id) REFERENCES dex_move(id),
    FOREIGN KEY(move_3_id) REFERENCES dex_move(id),
    FOREIGN KEY(move_4_id) REFERENCES dex_move(id)
);


-- -- Current enemy pokemon — enforced single row via CHECK (id = 1)
-- CREATE TABLE IF NOT EXISTS enemy_pokemon (
--     id         INTEGER PRIMARY KEY CHECK (id = 1),
--     pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
--     level      INTEGER NOT NULL DEFAULT 5,
--     current_hp INTEGER NOT NULL,
--     max_hp     INTEGER NOT NULL
-- );
