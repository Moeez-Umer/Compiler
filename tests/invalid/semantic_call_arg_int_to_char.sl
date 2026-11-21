// EXPECT: Semantic 6 Argument 1 of 'up': cannot pass int to char parameter 'c'
char up(char c) {
    return c;
}
int main() {
    char x = up(65);
    return 0;
}
