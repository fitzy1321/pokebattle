#ifndef MYLIB_H
#define MYLIB_H

#include <stddef.h>

void null_terminate(char *buf, size_t size) {
    buf[size - 1] = '\0';
}

#endif
