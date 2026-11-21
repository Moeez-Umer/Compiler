// EXPECT: OK
int sumRange(int n) {
    int sum = 0;
    for (int i = 1; i <= n; i = i + 1) {
        sum = sum + i;
    }
    int j = 0;
    for (j = 0; j < 2; j = j + 1) {
        sum = sum + j;
    }
    return sum;
}
