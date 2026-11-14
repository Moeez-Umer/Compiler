// Every SmartLang token class in one valid program (Phase 1 sample).
/* Block comment:
   spans two lines. */
const int LIMIT = 10;
const float RATE = 2.5;

int square(int x) {
    return x * x;
}

bool check(char c, int n) {
    return c == 'a' && n >= 0 || n != 1;
}

int main() {
    int total = 0;
    char c = '\n';
    char q = '\'';
    bool flag = !false;
    for (int i = 0; i < LIMIT; i = i + 1) {
        total = total + square(i) % 3 - 1;
    }
    while (total > 100) {
        total = total / 2;
    }
    if (check('a', total) && flag) {
        total = -total;
    } else {
        total = 0;
    }
    return total;
}
