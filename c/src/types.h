#pragma once

#define POKEDEX_COUNT 151

#define bool _Bool
#define true 1
#define false 0

// // Gen 1 Type Enum (matches internal game values)
// // ? Do I really need to make the gameboy internal values?
// // *Not really, this isn't a one to one simulation, just my silly C code.*
// typedef enum {
//     NORMAL   = 0x00,
//     FIGHTING = 0x01,
//     FLYING   = 0x02,
//     POISON   = 0x03,
//     GROUND   = 0x04,
//     ROCK     = 0x05,
//     BIRD     = 0x06, // Unused placeholder
//     BUG      = 0x07,
//     GHOST    = 0x08,
//     // 0x09 - 0x13: Unused "Normal" placeholders
//     FIRE     = 0x14,
//     WATER    = 0x15,
//     GRASS    = 0x16,
//     ELECTRIC = 0x17,
//     PSYCHIC  = 0x18,
//     ICE      = 0x19,
//     DRAGON   = 0x1A
// } Types;

typedef unsigned int uint;

typedef struct {
    uint id;                 // PK
    char name[64];
    char type_1[32];
    char type_2[32];         // nullable
    uint base_hp;
    uint base_attack;
    uint base_defense;
    uint base_sp_attack;
    uint base_sp_defense;
    uint base_speed;
    uint base_experience;
    char growth_rate[32];    // nullable
} Pokemon;

typedef struct {
    uint id;                 // PK
    char name[64];
    uint power;              // nullable
    uint accuracy;           // nullable
    uint max_pp;
    char type[32];           // nullable
    char damage_class[32];   // nullable
    char ailment[32];        // nullable
    int  ailment_chance;     // nullable
    char move_category[32];  // nullable
    int  healing;            // nullable
    int  drain;              // nullable
} Move;

typedef struct {
    uint id;                // PK
    uint pokemon_id;        // FK pokemon.id
    uint move_id;           // FK move.id
    uint level_learned;     // 0 = learns from the start
    char learn_method[32];  // nullable
} PokemonMove;

typedef struct {
    uint id; // PK
    uint pokemon_id;
    uint evolves_into_id;
    char trigger[32];
    uint min_level;
    char text[32];
    bool is_player_choice; // really int 'under the hood'
} PokemonEvolution;
