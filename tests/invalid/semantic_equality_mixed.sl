// EXPECT: Semantic 3 Operator '==' requires two numeric or two bool operands, found int and bool
int main() {
    bool r = 1 == true;
    return 0;
}
