// EXPECT: OK
// Function rules: forward calls, recursion, mutual recursion, widening arguments and returns.
int main() {
    float r = half(7);
    char c = next('a');
    int n = fact(5) + double_it('b');
    bool ok = even(4);
    twice(1);
    return n;
}

float half(float x) {
    return x / 2;
}

char next(char c) {
    return c;
}

int fact(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * fact(n - 1);
}

int double_it(int x) {
    return x * 2;
}

bool even(int n) {
    if (n == 0) {
        return true;
    }
    return odd(n - 1);
}

bool odd(int n) {
    if (n == 0) {
        return false;
    }
    return even(n - 1);
}

int twice(float x) {
    return 2;
}

float widen() {
    return 'x';
}
