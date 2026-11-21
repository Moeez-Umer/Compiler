// Demo: semantic errors only (the program is grammatical). TAC is skipped.
const int LIMIT = 10;

int square(int x) {
    return x * x;
}

int main() {
    int a = 2.5;
    int b = ghost + 1;
    bool flag = a;
    if (a + 1) {
    }
    LIMIT = 5;
    int c = square(1, 2);
    return a;
}
