#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <notcurses/direct.h>

#include "sql_ops.h"
#include "types.h"

// check for ending slash, will return "/" or "" str literals
static const char *slash_or_no_slash(const char *mstr) {
    size_t mlen = strlen(mstr);
    return (mstr[mlen - 1] != '/') ? "/" : "";
}

int get_db_path(char *out, size_t out_size) {
    const char *db_file_path = "pokebattle/pokedata.db";
    const char *home = getenv("HOME");
    const char *xdg_data = getenv("XDG_DATA_HOME");

    if (!xdg_data) {
        if (!home) return -1;

        // construct XDG_DATA path manually, with our application and db path
        snprintf(out, out_size, "%s%s.local/share/%s", home, slash_or_no_slash(home), db_file_path);
        return 0;
    }

    // add our application path to XDG_DATA path
    snprintf(out, out_size, "%s%s%s", xdg_data, slash_or_no_slash(xdg_data), db_file_path);
    return 0;
}

void print_pokedex(Pokemon dex[], size_t count){
    size_t i;
    Pokemon *p = NULL;
    for (i = 0; i < count; i++) {
        p = &dex[i];
        printf("Pokemon: %s. Id: %d\n", p->name, p->id);
    }
    p = NULL;
}

void free_sprites(Pokemon pokedex[], size_t count) {
    // todo should it be less than or less than and equal too.?
    Pokemon *p = NULL;
    for (size_t i = 0; i < count; i++) {
        printf("Freeing sprint data for Poke id: %zu\n", i+1);
        p = &pokedex[i];
        if (p->front_sprite_blob) {
            printf("Sprite data before free: %s\n", (char *)p->front_sprite_blob);
            free(p->front_sprite_blob);
            p->front_sprite_blob = NULL;
        }
        if (p->back_sprite_blob) {
            printf("Sprite data: %s\n",(char *)p->back_sprite_blob);
            free(p->back_sprite_blob);
            p->back_sprite_blob = NULL;
        }
        p = NULL;
    }
}

int _old_main(int _argc, char *_argv[]) {
    puts("\nWelcome to Pokémon Battle CLI!\n");

#ifdef DEV
    const char *db_path = "pokedata.db";
#else
    char db_path[256];
    int err = get_db_path(db_path, sizeof db_path);
    if (err) {
        perror("Could not get path to sqlite db.\nClosing with error ...\n");
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
    int rc = get_pokedex(db, pokedex, POKEDEX_COUNT);
    if (rc <= 0) {
        fprintf(stderr, "Error occured creating the pokedex: %s\n", sqlite3_errmsg(db));
        puts("Closing with error ...\n");
        sqlite3_close(db);
        return 1;
    }

    print_pokedex(pokedex, POKEDEX_COUNT);

    printf("Size of pokedex(in bytes): %zu\n", sizeof(pokedex));

    puts("Closing ...\n");
    sqlite3_close(db);

    // free all the sprite memory
    // free_sprites(pokedex, POKEDEX_COUNT);

    return 0;
}

int main(void) {
    struct notcurses_options opts = {
        .flags = NCOPTION_SUPPRESS_BANNERS,
    };
    struct notcurses *nc = notcurses_init(&opts, NULL);
    if (!nc) {
        perror("There was a problem starting the TUI!!!\nClosing ...\n");
        return 1;
    }
    struct ncplane *stdplane = notcurses_stdplane(nc);

    // Write text at row 2, col 4
    ncplane_set_fg_rgb8(stdplane, 0x00, 0xff, 0xaa);  // teal color
    ncplane_putstr_yx(stdplane, 2, 4, "Hello, Notcurses!");

    notcurses_render(nc);

    // Wait for key press
    ncinput ninput;
    notcurses_get_blocking(nc, &ninput);

    notcurses_stop(nc);
    return 0;
}
