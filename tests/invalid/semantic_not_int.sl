// EXPECT: Semantic 3 Operator '!' requires a bool operand, found int
int main() {
    bool r = !1;
    return 0;
}
