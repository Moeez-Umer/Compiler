// EXPECT: Semantic 2 'a' is already declared in this scope (line 2)
int f(int a, int a) {
    return a;
}
