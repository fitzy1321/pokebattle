default: build-and-run

API_DATA_DIR := "poke_api_data"
C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

build-and-run: compile run

alias bar := build-and-run

# build-db:
#     rm pokedata.db || true
#     ./pokedata

clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

compile:
    # #!/usr/bin/env bash
    # if [ ! -f "pokedata.db" ]; then
    #     ./pokedata
    # fi
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/main.c

fmt:
    just --fmt --unstable

# pip3 install -U marimo
marimo:
    marimo edit --watch

open-notebook:
    marimo edit --no-sandbox {{ API_DATA_DIR }}/gen1_data_notebook.py --watch

run:
    ./{{ C_BUILD_DIR }}/pokemain

setup_db:
    ./poke_api_data/compile_gen1_data.py
    ./poke_api_data/setup_db.py

test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
