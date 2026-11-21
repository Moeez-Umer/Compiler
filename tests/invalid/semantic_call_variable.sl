// EXPECT: Semantic 4 Cannot call 'x': it is a variable, not a function
int main() {
    int x = 1;
    return x(3);
}
