// EXPECT: OK
int x = 1;

int main() {
    int x = 2;
    {
        int x = 3;
        x = x + 1;
    }
    for (int x = 0; x < 2; x = x + 1) {
        int t1 = x;
        int L1 = t1 + 1;
    }
    return x;
}
