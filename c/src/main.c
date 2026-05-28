#include <stdio.h>
#include <stdlib.h>
#include <sqlite3.h>
#include <string.h>

#ifdef _WIN32
    #include <direct.h>
    #define m_getcwd _getcwd
#else
    #include <unistd.h>
    #define m_getcwd getcwd
#endif

// 1k might be overkill for a path string size
#define M_PATH_SIZE 1024

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

// typedef unsigned int uint;

// // Structure for a single Pokémon in the party or box
// // ?hmmmm which of these need to be in instance pokemon data and static data?
// typedef struct {
//     uint species;        // Species ID
//     uint hp;             // Current HP (low byte)
//     uint level;          // Current level
//     uint status;         // Status condition (e.g., sleep, poison)
//     uint type1;          // Primary type (PokemonType)
//     uint type2;          // Secondary type (PokemonType)
//     uint catch_rate;     // Catch rate (for wild Pokémon)
//     uint moves[4];       // Four move IDs
//     uint dv;            // Determinant Values (combined Attack, Defense, Speed, Special)
//     uint max_hp;        // Max HP
//     uint attack;        // Attack stat
//     uint defense;       // Defense stat
//     uint speed;         // Speed stat
//     uint special;       // Special stat (used for Spc Attack/Defense)
//     uint pp[4];          // PP for each move
// } Pokemon;

// void print_cwd() {
//     char buff[FILENAME_MAX];
//     if (m_getcwd(buff, FILENAME_MAX) != NULL) {
//         printf("\nC execution Current working directory: %s\n", buff);
//     } else {
//         perror("Error getting cwd");
//     }
// }

int get_sqlite_db_path(char *out, size_t out_size) {
    // TODO: what path should this be, and do I really care right now as long as it runs?
    const char *pokedb = "pokebattle/pokedata.db";
    char home_buf[M_PATH_SIZE];
    char xdg_buf[M_PATH_SIZE];
    const char *home = getenv("HOME");
    const char *xdg_data = getenv("XDG_DATA_HOME");

    if (!xdg_data) {
        if (!home) {
            return -1;
        }
        // deep copy HOME env, don't owe that memory
        snprintf(home_buf, M_PATH_SIZE, "%s", home);
        // TODO OS specific? For now XDG standard
        // check for ending slash
        size_t hlen = strlen(home);
        if (home[hlen - 1] != '/') {
            strncat(home_buf, "/", M_PATH_SIZE - hlen - 1);
        }
        snprintf(out, out_size, "%s%s%s", home_buf, ".local/share/", pokedb);
        return 0;
    }

    // deep copy XDG_DATA_HOME env, we don't own that memory
    snprintf(xdg_buf, M_PATH_SIZE, "%s", xdg_data);
    // check for ending slash
    size_t xlen = strlen(xdg_data);
    if (xdg_data[xlen - 1] != '/') {
        strncat(xdg_buf, "/", M_PATH_SIZE - xlen - 1);
    }
    // now make our path
    snprintf(out, out_size, "%s%s", xdg_buf, pokedb);
    return 0;
}

int main() {
    puts("Welcome to Pokémon Battle CLI!\n");
    #ifdef DEV
        const char *db_path = "pokedata.db";
    #else
        char db_path[M_PATH_SIZE];
        int err = get_sqlite_db_path(db_path, M_PATH_SIZE);
        if (err) {
            perror("Could not get path to sqlite db. Closing ...");
            return 1;
        }
    #endif
    printf("Sqlite DB Path: %s\n", db_path);

    // sqlite3 *db;
    // // char *zErrMsg = 0;

    // int rc = sqlite3_open(db_path, &db);
    // if (rc) {
    //     fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
    //     sqlite3_close(db);
    //     return 1;
    // }

    // // Pokemon *p1 = calloc(1, sizeof(Pokemon));
    // // p1->species=1;

    // // free(p1);

    // sqlite3_close(db);
    return 0;
}
