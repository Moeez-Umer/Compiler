// EXPECT: Semantic 6 Argument 1 of 'sq': cannot pass bool to int parameter 'n'
int sq(int n) {
    return n * n;
}
int main() {
    return sq(true);
}
