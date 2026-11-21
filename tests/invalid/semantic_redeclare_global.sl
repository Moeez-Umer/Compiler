// EXPECT: Semantic 3 'g' is already declared in this scope (line 2)
int g = 1;
int g = 2;
int main() {
    return g;
}
