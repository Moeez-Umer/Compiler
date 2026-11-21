// EXPECT: Semantic 3 Condition of 'for' must be bool, found int
int main() {
    for (int k = 0; k; k = k + 1) {
    }
    return 0;
}
