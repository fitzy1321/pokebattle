default:
    @just --list

all_c_files := "c/src/sql_ops.c c/src/main.c"

data_dir := "data"
c_build_dir := "c/build"
# C_SRC_DIR := "c/src"
# C_TEST_DIR := "c/tests"

notcurses_brew_prefix := `brew --prefix notcurses`
cflags := "-I" + notcurses_brew_prefix + "/include"
wflags := "-Wall -Werror"
ldflags := "-L" + notcurses_brew_prefix + "/lib -lnotcurses -lnotcurses-core -lsqlite3"

# Clean up C build files
clean:
    rm -rf {{ c_build_dir }}
    # should I delete the db and other files?
    # mkdir -p {{ c_build_dir }}

# Compile C Binary
compile:
    mkdir -p {{ c_build_dir }}
    cc -std=c23 \
        {{ wflags }} \
        {{ cflags }} \
        {{ ldflags }} \
        -o {{ c_build_dir }}/pokemain \
        {{ all_c_files }}

# Run the compiled C binary
run:
    ./{{ c_build_dir }}/pokemain

compile-and-run: compile run

alias car := compile-and-run

dev-compile:
    mkdir -p {{ c_build_dir }}
    cc -std=c23 \
        {{ wflags }} \
        {{ cflags }} \
        {{ ldflags }} \
        -DDEV \
        -o {{ c_build_dir }}/pokemain-dev \
        {{ all_c_files }}

dev-run:
    ./{{ c_build_dir }}/pokemain-dev

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

install-all-deps: setup_db install-cdeps

# open marimo server. pip3 install -U marimo
marimo:
    marimo edit --watch

# open the gen1_data marimo notebook
open-notebook:
    marimo edit --no-sandbox {{ data_dir }}/gen1_data_notebook.py --watch

# Call a couple python scripts to download pokeapi data and create a sqlite db
setup_db:
    ./{{ data_dir }}/compile_gen1_data.py

# # Run C "unit tests"
# test:
#     gcc -o {{ C_BUILD_DIR }}/test_runner \
#         {{ C_TEST_DIR }}/test_mylib.c
#     ./{{ C_BUILD_DIR }}/test_runner

venv-make:
    @test -d .venv || python3 -m venv .venv

venv-pip-up: venv-make
    .venv/bin/pip install -U pip && \
        .venv/bin/pip install -U ruff marimo typer requests

alias python-setup := venv-pip-up
