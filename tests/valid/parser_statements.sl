// EXPECT: OK
// Every statement type: declarations, assign, call statement, if/else-if/else,
// while, for (all three header forms), nested block and return.
const int LIMIT = 5;
float scale = 1.5;
bool ready;

int twice(int v) {
    return v + v;
}

int main() {
    int a = 1;
    const int B = 2;
    bool flag = true;
    int i;
    a = a + B;
    twice(a);
    {
        int inner = 3;
        a = a + inner;
    }
    if (a > LIMIT) {
        a = LIMIT;
    } else if (a == 0) {
        a = 1;
    } else {
        a = a - 1;
    }
    while (a < LIMIT) {
        a = a + 1;
    }
    for (int k = 0; k < 3; k = k + 1) {
        a = a + k;
    }
    for (i = 0; i < 3; i = i + 1) {
        a = a + i;
    }
    for (; a > 0; ) {
        a = a - 1;
    }
    return a;
}
