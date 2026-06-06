#include "sql_ops.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

sqlite3 *setup_db(const char *db_path) {
    sqlite3 *db = NULL;
    int rc = sqlite3_open(db_path, &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        db = NULL;
    }
    // turn on foreign keys
    sqlite3_exec(db, "PRAGMA foreign_keys = ON", NULL, NULL, NULL);
    return db;
}

static int safe_strcpy(char *dst, size_t dst_size, const char *src) {
    if (!dst || dst_size == 0)
        return 1;
    if (!src) {
        dst[0] = '\0';
        return 0;
    }

    size_t src_len = strlen(src);
    if (src_len >= dst_size) {
        memcpy(dst, src, dst_size - 1);
        dst[dst_size - 1] = '\0';
        return 1; /* truncated */
    }
    memcpy(dst, src, src_len + 1);
    return 0;
}

static void row_to_pokemon_t(sqlite3_stmt *stmt, Pokemon *p) {
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
    p->base_hp = sqlite3_column_int(stmt, 4);
    p->base_attack = sqlite3_column_int(stmt, 5);
    p->base_defense = sqlite3_column_int(stmt, 6);
    p->base_sp_attack = sqlite3_column_int(stmt, 7);
    p->base_sp_defense = sqlite3_column_int(stmt, 8);
    p->base_speed = sqlite3_column_int(stmt, 9);

    // base_experience, INT nullable
    if (sqlite3_column_type(stmt, 10) != SQLITE_NULL) {
        p->base_experience = sqlite3_column_int(stmt, 10);
    }

    // growth_rate, TEXT nullable
    if (sqlite3_column_type(stmt, 11) != SQLITE_NULL) {
        col = (const char *)sqlite3_column_text(stmt, 11);
        truncated |= safe_strcpy(p->growth_rate, sizeof(p->growth_rate), col);
    }

    // // front_sprite, blob NULLABLE (png sprite)
    if (sqlite3_column_type(stmt, 12) != SQLITE_NULL) {
        const void *front_sprite_blob = sqlite3_column_blob(stmt, 12);
        if (front_sprite_blob) {
            printf("Front sprite data: %s\n", (char *)front_sprite_blob);
            p->front_sprite_size = sqlite3_column_bytes(stmt, 12);
            //! MUST BE FREED LATER !
            p->front_sprite_blob = malloc(p->front_sprite_size);
            memcpy(p->front_sprite_blob, front_sprite_blob, p->front_sprite_size);
        } else {
            p->front_sprite_blob = NULL;
            p->front_sprite_size = 0;
        }
    } else {
        p->front_sprite_blob = NULL;
        p->front_sprite_size = 0;
    }

    // back_sprite, blob NULLABLE (png sprite)
    if (sqlite3_column_type(stmt, 13) != SQLITE_NULL) {
        const void *back_blob = sqlite3_column_blob(stmt, 13);
        if (back_blob) {
            puts("adding back sprite!");
            p->back_sprite_size = sqlite3_column_bytes(stmt, 13);
            //! MUST BE FREED LATER !
            p->back_sprite_blob = malloc(p->back_sprite_size);
            memcpy(p->back_sprite_blob, back_blob, p->back_sprite_size);
        } else {
            p->back_sprite_blob = NULL;
            p->back_sprite_size = 0;
        }
    } else {
        p->back_sprite_blob = NULL;
        p->back_sprite_size = 0;
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
int get_pokedex(sqlite3 *db, Pokemon dex_out[]) {
    sqlite3_stmt *stmt = NULL;
    static const char sql_str[] = "SELECT id, name, type_1, type_2,"
                                  "       base_hp, base_attack, base_defense,"
                                  "       base_sp_attack, base_sp_defense, base_speed,"
                                  "       base_experience, growth_rate"
                                  "  FROM dex_pokemon"
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
    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        row_to_pokemon_t(stmt, &dex_out[count++]);
    }

    sqlite3_finalize(stmt);
    stmt = NULL;

    if (rc != SQLITE_DONE) {
        return -1;
    }

    return count;
}
