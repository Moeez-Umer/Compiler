// EXPECT: OK
int main() {
    int total = 0;
    for (int i = 0; i < 3; i = i + 1) {
        int j = 0;
        while (j < 2) {
            if (i == j) {
                total = total + 10;
            } else {
                total = total + 1;
            }
            j = j + 1;
        }
    }
    return total;
}
