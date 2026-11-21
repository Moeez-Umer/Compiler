// EXPECT: Semantic 4 Operator '<' requires numeric operands, found bool and int
int main() {
    bool b = true;
    bool r = b < 1;
    return 0;
}
