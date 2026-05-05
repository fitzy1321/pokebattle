default:
    @just --list

open-marimo:
    marimo edit --sandbox data/pokedata_notebook.py --watch

compile-c:
    @mkdir -p c/build
    cc -std=c11 -Wall -Werror c/src/main.c -o c/build/main

test:
    @mkdir -p c/build/tests
    gcc -o c/build/tests/test_mylib c/tests/test_mylib.c
    ./c/build/tests/test_mylib
