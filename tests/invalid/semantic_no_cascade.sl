// EXPECT: Semantic 4 Operator '+' requires numeric operands, found bool and int
// EXPECT: Semantic 5 Operator '-' requires numeric operands, found bool and int
int main() {
    int x = (true + 1) * 2 + 3;
    if ((false - 1) * 2) {
    }
    return x;
}
