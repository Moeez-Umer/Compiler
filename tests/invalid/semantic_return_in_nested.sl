// EXPECT: Semantic 5 Cannot return bool from function 'f' returning int
int f(int n) {
    while (n > 0) {
        if (n == 1) {
            return true;
        }
        n = n - 1;
    }
    return 0;
}
