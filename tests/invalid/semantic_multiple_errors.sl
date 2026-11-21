// EXPECT: Semantic 8 Cannot assign float to int variable 'x'
// EXPECT: Semantic 9 Undeclared identifier 'ghost'
// EXPECT: Semantic 10 Operator '%' requires int or char operands, found float and int
// EXPECT: Semantic 11 Condition of 'if' must be bool, found int
// EXPECT: Semantic 13 Cannot assign to constant 'LIMIT'
const int LIMIT = 3;
int main() {
    int x = 2.5;
    int y = ghost + 1;
    float z = 1.5 % 2;
    if (x + 1) {
    }
    LIMIT = 4;
    return x;
}
