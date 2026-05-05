#ifndef UNITY_H
#define UNITY_H

#include <stdio.h>
#include <stdlib.h>

static int unity_failures = 0;
static int unity_tests = 0;
static const char *unity_current_test = "";

#define UNITY_BEGIN() (unity_failures = 0, unity_tests = 0)
#define UNITY_END() (printf("\n%d tests, %d failures\n", unity_tests, unity_failures), unity_failures)

#define RUN_TEST(t) do { \
    unity_current_test = #t; \
    unity_tests++; \
    t(); \
} while(0)

#define TEST_ASSERT_EQUAL_CHAR(expected, actual) do { \
    if ((expected) != (actual)) { \
        printf("FAIL: %s — expected '%c' (0x%02x) but got '%c' (0x%02x)\n", \
            unity_current_test, (expected), (unsigned char)(expected), \
            (actual), (unsigned char)(actual)); \
        unity_failures++; \
    } else { \
        printf("PASS: %s\n", unity_current_test); \
    } \
} while(0)

#endif
