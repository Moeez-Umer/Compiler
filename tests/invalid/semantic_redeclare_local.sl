// EXPECT: Semantic 4 'a' is already declared in this scope (line 3)
int main() {
    int a = 1;
    int a = 2;
    return a;
}
