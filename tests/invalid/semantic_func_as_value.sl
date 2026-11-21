// EXPECT: Semantic 6 Function 'f' cannot be used as a variable
int f() {
    return 1;
}
int main() {
    int x = f;
    return x;
}
