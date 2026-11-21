// EXPECT: Semantic 5 Cannot assign to constant 'i'
// EXPECT: Semantic 5 Cannot assign to constant 'i'
int main() {
    const int i = 0;
    for (i = 0; i < 3; i = i + 1) {
    }
    return 0;
}
