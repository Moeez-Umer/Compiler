// EXPECT: Semantic 6 Function 'add' expects 2 arguments, found 1
int add(int a, int b) {
    return a + b;
}
int main() {
    return add(1);
}
