default: build-and-run

C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

build-and-run: compile run

alias bar := build-and-run

build-db:
    rm pokedata.db || true
    ./claude_etl

clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

compile:
    #!/usr/bin/env bash
    if [ ! -f "pokedata.db" ]; then
        ./claude_etl
    fi
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/main.c

# pip3 install -U marimo
data-notebook:
    marimo edit --sandbox pokedata_notebook.py --watch

fmt:
    just --fmt --unstable

run:
    ./{{ C_BUILD_DIR }}/pokemain

test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
