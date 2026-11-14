// EXPECT: OK
// Token-level sample: every operator and delimiter, with longest-match cases.
int main() {
    int a = 1;
    int b = 2;
    bool lt = a < b;
    bool le = a <= b;
    bool gt = a > b;
    bool ge = a >= b;
    bool eq = a == b;
    bool ne = a != b;
    bool both = lt && le;
    bool either = gt || ge;
    bool neg = !eq;
    int arith = a + b - a * b / b % 2;
    int minus = -a;
    return arith + minus;
}
