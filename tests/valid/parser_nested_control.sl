// EXPECT: OK
// Nested loops, nested if/else-if chains and recursion through a call in an expression.
int fact(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * fact(n - 1);
}

int main() {
    int total = 0;
    for (int i = 0; i < 4; i = i + 1) {
        int j = 0;
        while (j < i) {
            for (int k = 0; k < j; k = k + 1) {
                if (k == 0) {
                    total = total + 1;
                } else if (k == 1) {
                    if (j > 1) {
                        total = total + 2;
                    } else {
                        total = total + 3;
                    }
                } else {
                    total = total + fact(k);
                }
            }
            j = j + 1;
        }
    }
    return total;
}
