// EXPECT: Semantic 6 Missing return at end of function 'f'
int f(int n) {
    while (n > 0) {
        return n;
    }
}
