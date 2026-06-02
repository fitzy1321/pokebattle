#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sql_ops.h"
#include "types.h"

// check for ending slash, will return "/" or ""
static const char *slash_or_no_slash(const char *mstr) {
    size_t mlen = strlen(mstr);
    return (mstr[mlen - 1] != '/') ? "/" : "";
}

int get_db_path(char *out, size_t out_size) {
    const char *db_file_path = "pokebattle/pokedata.db";
    const char *home = getenv("HOME");
    const char *xdg_data = getenv("XDG_DATA_HOME");

    if (!xdg_data) {
        if (!home)
            return -1;

        // construct XDG_DATA path manually, with our application and db path
        snprintf(out, out_size, "%s%s.local/share/%s", home, slash_or_no_slash(home), db_file_path);
        return 0;
    }

    // add our application path to XDG_DATA path
    snprintf(out, out_size, "%s%s%s", xdg_data, slash_or_no_slash(xdg_data), db_file_path);
    return 0;
}

int main(int _argc, char *_argv[]) {
    puts("\nWelcome to Pokémon Battle CLI!\n");

#ifdef DEV
    const char *db_path = "pokedata.db";
#else
    char db_path[256];
    int err = get_db_path(db_path, sizeof db_path);
    if (err) {
        perror("Could not get path to sqlite db.\nClosing ...");
        return 1;
    }
#endif

    sqlite3 *db = setup_db(db_path);
    if (!db) {
        // setup func already displays error message, and closes the db if in a
        // failed state
        puts("Closing with error ...\n");
        return 1;
    }

    Pokemon pokedex[POKEDEX_COUNT];
    int rc = get_pokedex(db, pokedex);
    if (rc <= 0) {
        fprintf(stderr, "Error occured creating the pokedex: %s\n", sqlite3_errmsg(db));
        puts("Closing with error ...\n");
        sqlite3_close(db);
        return 1;
    }

    int i;
    Pokemon *p = NULL;
    for (i = 0; i < POKEDEX_COUNT; i++) {
        p = &pokedex[i];
        printf("Pokemon: %s. Id: %d\n", p->name, p->id);
    }
    p = NULL;

    printf("Size of pokedex(in bytes): %zu\n", sizeof(pokedex));

    puts("Closing ...\n");
    sqlite3_close(db);

    return 0;
}
