default:
    @just --list

DATA_DIR := "data"
C_BUILD_DIR := "c/build"
# C_SRC_DIR := "c/src"
C_TEST_DIR := "c/tests"

ALL_C_FILES := "c/src/sql_ops.c c/src/main.c"

notcurses_brew_prefix := `brew --prefix notcurses`

cflags := "-I" + notcurses_brew_prefix + "/include"
wflags := "-Wall -Werror"
ldflags := "-L" + notcurses_brew_prefix + "/lib -lnotcurses -lsqlite3"

# Clean up C build files
clean:
    rm -rf {{ C_BUILD_DIR }}
    mkdir -p {{ C_BUILD_DIR }}

# Compile C Binary
compile:
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c18 {{ cflags }} {{ wflags }} {{ ldflags }} \
        -o {{ C_BUILD_DIR }}/pokemain \
        {{ ALL_C_FILES }}

# Run the compiled C binary
run:
    ./{{ C_BUILD_DIR }}/pokemain

compile-and-run: compile run

alias car := compile-and-run

dev-compile:
    mkdir -p {{ C_BUILD_DIR }}
    cc -std=c18 {{ cflags }} {{ wflags }} {{ ldflags }} -DDEV \
        -o {{ C_BUILD_DIR }}/pokemain-dev \
        {{ ALL_C_FILES }}

dev-run:
    ./{{ C_BUILD_DIR }}/pokemain-dev

dev-compile-and-run: dev-compile dev-run

# ! Use this one, to run in the repo folder !
alias dar := dev-compile-and-run

# formats just file only
fmt:
    just --fmt --unstable

install-cdeps:
    # install notcurses and setup zed editor to find include path
    brew install notcurses && \
        echo {{ cflags }} > compile_flags.txt

# open marimo server. pip3 install -U marimo
marimo:
    marimo edit --watch

# open the gen1_data marimo notebook
open-notebook:
    marimo edit --no-sandbox {{ DATA_DIR }}/gen1_data_notebook.py --watch

# Call a couple python scripts to download pokeapi data and create a sqlite db
setup_db:
    ./{{ DATA_DIR }}/compile_gen1_data.py -h
    # ./{{ DATA_DIR }}/setup_db.py -h

# Run C "unit tests"
test:
    gcc -o {{ C_BUILD_DIR }}/test_runner \
        {{ C_TEST_DIR }}/test_mylib.c
    ./{{ C_BUILD_DIR }}/test_runner
