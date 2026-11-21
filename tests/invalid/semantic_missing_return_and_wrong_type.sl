// EXPECT: Semantic 4 Cannot return float from function 'f' returning int
// EXPECT: Semantic 6 Missing return at end of function 'f'
int f() {
    return 1.5;
    int x = 1;
}
