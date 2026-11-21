// EXPECT: OK
int inc(int x) {
    return x + 1;
}

int combine(int a, int b) {
    return a * 10 + b;
}

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

int main() {
    int a = 2;
    int b = 3;
    inc(a);
    int y = combine(a, inc(b));
    int f = factorial(4);
    return y + f;
}
