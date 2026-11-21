// EXPECT: OK
const int LIMIT = 10;

int square(int x) {
    return x * x;
}

int sumSquares(int n) {
    int total = 0;
    int i = 1;
    while (i <= n) {
        total = total + square(i);
        i = i + 1;
    }
    return total;
}

float average(int a, int b) {
    float s = a + b;
    return s / 2;
}

int main() {
    int r = sumSquares(LIMIT);
    bool big = r > 100 && LIMIT != 0;
    if (big) {
        r = r - 1;
    } else if (r == 0) {
        r = 1;
    } else {
        r = 0;
    }
    for (int k = 0; k < 3; k = k + 1) {
        r = r + k;
    }
    return r;
}
