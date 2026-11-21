// EXPECT: Semantic 7 Operator '+' requires numeric operands, found bool and int
// EXPECT: Semantic 7 Function 'add' expects 2 arguments, found 3
int add(int a, int b) {
    return a + b;
}
int main() {
    return add(true + 1, 2, 3);
}
