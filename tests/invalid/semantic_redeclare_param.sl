// EXPECT: Semantic 3 'a' is already declared in this scope (line 2)
int f(int a) {
    int a = 1;
    return a;
}
