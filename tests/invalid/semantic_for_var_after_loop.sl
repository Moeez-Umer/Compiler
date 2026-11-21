// EXPECT: Semantic 5 Undeclared identifier 'k'
int main() {
    for (int k = 0; k < 3; k = k + 1) {
    }
    return k;
}
