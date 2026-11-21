// EXPECT: Semantic 4 Operator '-' requires a numeric operand, found bool
int main() {
    bool b = true;
    int n = -b;
    return n;
}
