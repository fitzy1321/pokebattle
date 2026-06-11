#pragma once

#include <sqlite3.h>
#include "types.h"

sqlite3 *setup_db(const char *);

int get_pokedex(sqlite3 *, Pokemon[], size_t);
