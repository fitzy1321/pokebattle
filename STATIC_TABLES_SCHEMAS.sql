DROP TABLE IF EXISTS pokemon;
CREATE TABLE pokemon (
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

DROP TABLE IF EXISTS moves;
CREATE TABLE moves (
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

DROP TABLE IF EXISTS pokemon_moves;
CREATE TABLE pokemon_moves (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id    INTEGER NOT NULL,       -- FK pokemon(id)
    move_id       INTEGER NOT NULL,       -- FK moves(id)
    level_learned INTEGER NOT NULL,       -- 0 = learned at start
    learn_method  TEXT,
    FOREIGN KEY(pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY(move_id) REFERENCES moves(id),
    UNIQUE(pokemon_id, move_id)
);

DROP TABLE IF EXISTS pokemon_evolutions;
CREATE TABLE pokemon_evolutions (
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
