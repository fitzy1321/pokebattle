#ifndef MYLIB_H
#define MYLIB_H

#include <stddef.h>

void null_terminate(char *buf, size_t size) {
    buf[size - 1] = '\0';
}

typedef struct {
    void *items;
    size_t length;
    size_t capacity;
} array_t;

void array_bounds_check(array_t array, size_t index) {
    if (index >= 0 && index < array.length) { // always less, not less or equal
        return array.items[index];
    }

    return;
}

#endif
