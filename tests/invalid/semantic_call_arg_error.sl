// EXPECT: Semantic 6 Operator '+' requires numeric operands, found bool and int
int one(int a) {
    return a;
}
int main() {
    return one(true + 1);
}
