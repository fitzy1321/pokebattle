#include "unity.h"
#include "mylib.h"

// Unity requires these two — runs before/after each test
void setUp(void) {}
void tearDown(void) {}

void test_last_byte_is_null(void) {
    char buf[10] = "helloworld";  // no null terminator
    null_terminate(buf, 10);
    TEST_ASSERT_EQUAL_CHAR('\0', buf[9]);
}

void test_does_not_touch_earlier_bytes(void) {
    char buf[5] = {'a', 'b', 'c', 'd', 'e'};
    null_terminate(buf, 5);
    TEST_ASSERT_EQUAL_CHAR('a', buf[0]);
    TEST_ASSERT_EQUAL_CHAR('b', buf[1]);
    TEST_ASSERT_EQUAL_CHAR('c', buf[2]);
    TEST_ASSERT_EQUAL_CHAR('d', buf[3]);
    TEST_ASSERT_EQUAL_CHAR('\0', buf[4]);
}

void test_size_one_buffer(void) {
    char buf[1] = {'x'};
    null_terminate(buf, 1);
    TEST_ASSERT_EQUAL_CHAR('\0', buf[0]);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_last_byte_is_null);
    RUN_TEST(test_does_not_touch_earlier_bytes);
    RUN_TEST(test_size_one_buffer);
    return UNITY_END();
}
