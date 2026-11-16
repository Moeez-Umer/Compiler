// EXPECT: OK
// Precedence, associativity, unary operators, parentheses and calls inside expressions.
int add3(int x, int y, int z) {
    return x + y + z;
}

int main() {
    int a = 1;
    int b = 2;
    int c = 3;
    int sum = 1 + 2 * 3;
    int diff = a - b - c;
    int mixed = (a + b) * c % 2 - -a;
    bool logic = a < b || b < c && c != 0;
    bool chain = a == b != false;
    bool negated = !(a >= b) && !false;
    int nested = add3(add3(a, b, c), b * 2, -c);
    return sum + diff + mixed + nested;
}
