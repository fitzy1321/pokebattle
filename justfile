default:
    @just --list

DATA_DIR := "data"
C_BUILD_DIR := "c/build"
C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

# Clean up C build files
clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

# Compile C Binary
compile:
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -o {{ C_BUILD_DIR }}/pokemain \
        {{ C_SRC_DIR }}/sql_ops.c \
        {{ C_SRC_DIR }}/main.c

# Run the compiled C binary
run:
    ./{{ C_BUILD_DIR }}/pokemain

compile-and-run: compile run

alias car := compile-and-run

dev-compile:
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c11 -Wall -Werror -lsqlite3 -DDEV -o {{ C_BUILD_DIR }}/pokemain-dev \
        {{ C_SRC_DIR }}/sql_ops.c \
        {{ C_SRC_DIR }}/main.c

dev-run:
    ./{{ C_BUILD_DIR }}/pokemain-dev

dev-compile-and-run: dev-compile dev-run

# ! Use this one, to run in the repo folder !
alias dar := dev-compile-and-run

# formats just file only
fmt:
    just --fmt --unstable

# open marimo server. pip3 install -U marimo
marimo:
    marimo edit --watch

# open the gen1_data marimo notebook
open-notebook:
    marimo edit --no-sandbox {{ DATA_DIR }}/gen1_data_notebook.py --watch

# Call a couple python scripts to download pokeapi data and create a sqlite db
setup_db:
    ./{{ DATA_DIR }}/compile_gen1_data.py
    ./{{ DATA_DIR }}/setup_db.py

# Run C "unit tests"
test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
