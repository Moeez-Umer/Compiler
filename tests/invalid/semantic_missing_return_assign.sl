// EXPECT: Semantic 5 Missing return at end of function 'f'
int f(int a) {
    int x = a;
    x = x + 1;
}
