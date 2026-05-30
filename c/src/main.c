#include <stdio.h>
#include <stdlib.h>
#include <sqlite3.h>
#include <string.h>

#define POKEDEX_COUNT 151

// #ifdef _WIN32
//     #include <direct.h>
//     #define m_getcwd _getcwd
// #else
//     #include <unistd.h>
//     #define m_getcwd getcwd
// #endif

// void print_cwd() {
//     char buff[FILENAME_MAX];
//     if (m_getcwd(buff, FILENAME_MAX) != NULL) {
//         printf("\nC execution Current working directory: %s\n", buff);
//     } else {
//         perror("Error getting cwd");
//     }
// }


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

// "Static" Pokemon Data
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

static int safe_strcpy(char *dst, size_t dst_size, const char *src) {
    if (!dst || dst_size == 0) return 1;
    if (!src) { dst[0] = '\0'; return 0; }

    size_t src_len = strlen(src);
    if (src_len >= dst_size) {
        memcpy(dst, src, dst_size - 1);
        dst[dst_size - 1] = '\0';
        return 1;   /* truncated */
    }
    memcpy(dst, src, src_len + 1);
    return 0;
}

static void row_to_pokemon(sqlite3_stmt *stmt, Pokemon *p) {
    const char *col;
    int truncated = 0;

    // fill empty values for null fields, all fields get set though...
    memset(p, 0, sizeof(*p));

    // id, int PK field
    p->id = sqlite3_column_int(stmt, 0);
    // name, TEXT field
    col = (const char *)sqlite3_column_text(stmt, 1);
    truncated |= safe_strcpy(p->name, sizeof(p->name), col);

    // type 1, TEXT Field
    col = (const char *)sqlite3_column_text(stmt, 2);
    truncated |= safe_strcpy(p->type_1, sizeof(p->type_1), col);

    // type_2, TEXT nullable
    if (sqlite3_column_type(stmt, 3) != SQLITE_NULL) {
        col = (const char *)sqlite3_column_text(stmt, 3);
        truncated |= safe_strcpy(p->type_2, sizeof(p->type_2), col);
    }

    // All the next are required int fields
    p->base_hp          = sqlite3_column_int(stmt, 4);
    p->base_attack      = sqlite3_column_int(stmt, 5);
    p->base_defense     = sqlite3_column_int(stmt, 6);
    p->base_sp_attack   = sqlite3_column_int(stmt, 7);
    p->base_sp_defense  = sqlite3_column_int(stmt, 8);
    p->base_speed       = sqlite3_column_int(stmt, 9);

    // base_experience, INT nullable
    if (sqlite3_column_type(stmt, 10) != SQLITE_NULL) {
        p->base_experience = sqlite3_column_int(stmt, 10);
    }

    // growth_rate, TEXT nullable
    if (sqlite3_column_type(stmt, 11) != SQLITE_NULL) {
        col = (const char *)sqlite3_column_text(stmt, 11);
        truncated |= safe_strcpy(p->growth_rate, sizeof(p->growth_rate), col);
    }

    if (truncated) {
        fprintf(stderr, "warning: data truncated for pokemon id=%d\n", p->id);
    }
}


/*
This function will get data from Pokemon Table in sqlite3, and turn them into
Pokemon structs, and into the dex array.

Input:
    sqlite *db: pointer to sqlite3 db, where all the data lives
    Pokemon dex[]: basically a pointer to an array of Pokemon structs.

Output:
    int: Postive value is the count (should always be 151).
         A zero or negative value means an error occured.
*/
static int get_pokedex(sqlite3 *db, Pokemon dex[]) {
    sqlite3_stmt *stmt = NULL;
    static const char sql_str[] =
        "SELECT id, name, type_1, type_2,"
        "       base_hp, base_attack, base_defense,"
        "       base_sp_attack, base_sp_defense, base_speed,"
        "       base_experience, growth_rate"
        "  FROM pokemon"
        " ORDER BY id"
        " LIMIT ?";


    int rc = sqlite3_prepare_v2(db, sql_str, -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        return -1;
    }

    rc = sqlite3_bind_int(stmt, 1, POKEDEX_COUNT);
    if (rc != SQLITE_OK) {
        return -1;
    }

    int count = 0;
    while((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        row_to_pokemon(stmt, &dex[count++]);
    }

    sqlite3_finalize(stmt);
    stmt = NULL;

    if (rc != SQLITE_DONE) {
        return -1;
    }

    return count;
}

int get_db_path(char *out, size_t out_size) {
    const char *pokedb = "pokebattle/pokedata.db";
    const char *home = getenv("HOME");
    const char *xdg_data = getenv("XDG_DATA_HOME");

    if (!xdg_data) {
        if (!home) return -1;
        // check for ending slash
        size_t hlen = strlen(home);
        const char *slash = (home[hlen - 1] != '/') ? "/" : "";
        // construct XDG_DATA path manually, with our application and db path
        snprintf(out, out_size, "%s%s.local/share/%s", home, slash, pokedb);
        return 0;
    }

    // check for ending slash
    size_t xlen = strlen(xdg_data);
    const char *slash = (xdg_data[xlen - 1] != '/') ? "/" : "";
    // add our application path to XDG_DATA path
    snprintf(out, out_size, "%s%s%s", xdg_data, slash, pokedb);
    return 0;
}


sqlite3 *setup_db(void) {
    #ifdef DEV
        const char *db_path = "pokedata.db";
    #else
        char db_path[256];
        int err = get_db_path(db_path, sizeof db_path);
        if (err) {
            perror("Could not get path to sqlite db.\nClosing ...");
            return NULL;
        }
    #endif
    // printf("Sqlite DB Path: %s\n", db_path);

    sqlite3 *db = NULL;
    int rc = sqlite3_open(db_path, &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return NULL;
    }
    return db;
}

int main(int argc, char *argv[]) {
    puts("\nWelcome to Pokémon Battle CLI!\n");

    sqlite3 *db = setup_db();
    if (!db) {
        // func already displays error message
        puts("Closing with error ...\n");
        return 1;
    }

    Pokemon pokedex[POKEDEX_COUNT];
    int rc = get_pokedex(db, pokedex);
    if (rc <= 0) {
        fprintf(stderr, "Error occured creating the pokedex: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }

    Pokemon *p = NULL;
    for (int i = 0; i < POKEDEX_COUNT; i++) {
        p = &pokedex[i];
        printf("Pokemon: %s. Id: %d\n", p->name, p->id);
    }
    p = NULL;

    puts("Closing ...\n");
    sqlite3_close(db);

    return 0;
}
