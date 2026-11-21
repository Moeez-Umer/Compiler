// EXPECT: OK
int findThreshold(int limit) {
    int acc = 1;
    int step = 0;
    while (step < 10) {
        acc = acc * 2;
        if (acc >= limit) {
            return acc;
        }
        step = step + 1;
    }
    return acc;
}
