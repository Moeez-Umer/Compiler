// EXPECT: OK
int main() {
    int a = 10;
    int b = 3;
    int c = 2;
    int x = a + b * c;
    int y = a - b - c;
    int z = (a + b) * (c % 2 + 1) / 3;
    bool ok = a > b && b <= c || a != c && b == 3;
    if (ok) {
        return x + y;
    }
    return z;
}
