// EXPECT: Semantic 3 Operator '+' requires numeric operands, found bool and int
int main() {
    int y = true + 1;
    return y;
}
