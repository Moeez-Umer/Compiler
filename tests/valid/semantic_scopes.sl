// EXPECT: OK
// Scopes: shadowing, parameter shadowed in a nested block, for scope, forward call, recursion, globals.
const int BASE = 2;
int total = BASE * 3;
int count(int n) {
    if (n <= 0) {
        return 0;
    }
    {
        int n = 5;
        total = total + n;
    }
    return later(n - 1) + count(n - 1);
}
int later(int m) {
    for (int k = 0; k < m; k = k + 1) {
        int k = 7;
        total = total + k;
    }
    for (int k = 0; k < 2; k = k + 1) {
        total = total + k;
    }
    return total;
}
int main() {
    int total = 1;
    int t1 = 2;
    return count(total + t1);
}
