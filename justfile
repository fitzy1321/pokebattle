default:
    @just --list

C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

build-db:
    rm pokedata.db || true
    ./claude_etl

clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

compile:
    @mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/main.c

compile-run: compile
    ./{{ C_BUILD_DIR }}/pokemain

alias cr := compile-run

fmt:
    just --fmt --unstable

# pip3 install -U marimo
open-marimo:
    marimo edit --sandbox pokedata_notebook.py --watch

test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
