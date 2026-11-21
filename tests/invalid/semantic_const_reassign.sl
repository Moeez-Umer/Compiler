// EXPECT: Semantic 4 Cannot assign to constant 'c'
int main() {
    const int c = 1;
    c = 2;
    return c;
}
