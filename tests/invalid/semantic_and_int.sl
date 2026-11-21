// EXPECT: Semantic 3 Operator '&&' requires bool operands, found int and bool
int main() {
    bool r = 1 && true;
    return 0;
}
