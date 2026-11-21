// EXPECT: OK
int classify(int n) {
    int tag = 0;
    if (n < 0) {
        if (n < -10) {
            return -2;
        }
        tag = -1;
    } else if (n == 0) {
        tag = 0;
    } else if (n < 10) {
        tag = 1;
    } else {
        tag = 2;
    }
    return tag;
}
