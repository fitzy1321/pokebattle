default:
    @just --list

open-marimo:
    marimo edit --sandbox data/pokedata_notebook.py --watch

C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

compile:
    @mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/main.c
compile-run: compile
    ./{{ C_BUILD_DIR }}/pokemain

alias cr := compile-run

test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
