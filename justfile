# default = just --list
default:
    @just --list

API_DATA_DIR := "poke_api_data"
C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

# build-db:
#     rm pokedata.db || true
#     ./pokedata

# Clean up C build files
clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

# Create C binary
compile:
    # #!/usr/bin/env bash
    # if [ ! -f "pokedata.db" ]; then
    #     ./pokedata
    # fi
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/main.c

compile-and-run: compile run

alias car := compile-and-run

# formats just file only
fmt:
    just --fmt --unstable

# open marimo server. pip3 install -U marimo
marimo:
    marimo edit --watch

# open the poke-api marimo notebook
open-notebook:
    marimo edit --no-sandbox {{ API_DATA_DIR }}/gen1_data_notebook.py --watch

# Run the compiled C binary
run:
    ./{{ C_BUILD_DIR }}/pokemain

# Call a couple python scripts to download pokeapi data and create a sqlite db
setup_db:
    ./{{ API_DATA_DIR }}/compile_gen1_data.py
    ./{{ API_DATA_DIR }}/setup_db.py

# Run C "unit tests"
test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
