// EXPECT: Semantic 4 Cannot call 'x': it is a variable, not a function
int main() {
    int x = 1;
    x(2);
    return 0;
}
