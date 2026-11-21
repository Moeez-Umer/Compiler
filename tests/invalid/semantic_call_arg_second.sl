// EXPECT: Semantic 6 Argument 2 of 'add': cannot pass bool to int parameter 'b'
int add(int a, int b) {
    return a + b;
}
int main() {
    return add(1, false);
}
