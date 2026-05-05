#include <stdio.h>
#include <stdlib.h>
#include <sqlite3.h>

// Gen 1 Type Enum (matches internal game values)
// ? Do I really need to make the gameboy internal values?
// *Not really, this isn't a one to one simulation, just my silly C code.*
typedef enum {
    NORMAL   = 0x00,
    FIGHTING = 0x01,
    FLYING   = 0x02,
    POISON   = 0x03,
    GROUND   = 0x04,
    ROCK     = 0x05,
    BIRD     = 0x06, // Unused placeholder
    BUG      = 0x07,
    GHOST    = 0x08,
    // 0x09 - 0x13: Unused "Normal" placeholders
    FIRE     = 0x14,
    WATER    = 0x15,
    GRASS    = 0x16,
    ELECTRIC = 0x17,
    PSYCHIC  = 0x18,
    ICE      = 0x19,
    DRAGON   = 0x1A
} Types;

typedef unsigned int uint;

// Structure for a single Pokémon in the party or box
// ?hmmmm which of these need to be in instance pokemon data and static data?
typedef struct {
    uint species;        // Species ID
    uint hp;             // Current HP (low byte)
    uint level;          // Current level
    uint status;         // Status condition (e.g., sleep, poison)
    uint type1;          // Primary type (PokemonType)
    uint type2;          // Secondary type (PokemonType)
    uint catch_rate;     // Catch rate (for wild Pokémon)
    uint moves[4];       // Four move IDs
    uint dv;            // Determinant Values (combined Attack, Defense, Speed, Special)
    uint max_hp;        // Max HP
    uint attack;        // Attack stat
    uint defense;       // Defense stat
    uint speed;         // Speed stat
    uint special;       // Special stat (used for Spc Attack/Defense)
    uint pp[4];          // PP for each move
} Pokemon;


int main() {
    printf("Welcome to Pokémon Battle CLI!\n");

    sqlite3 *db;
    // TODO: what path should this be, and do I really care right now as long as it runs?
    int rc = sqlite3_open("pokedata.db", &db);
    if (rc) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    Pokemon *p1 = calloc(1, sizeof(Pokemon));
    p1->species=1;

    free(p1);

    return 0;
}
