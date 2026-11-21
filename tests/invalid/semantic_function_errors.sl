// EXPECT: Semantic 11 Cannot return float from function 'half' returning int
// EXPECT: Semantic 15 Missing return at end of function 'noret'
// EXPECT: Semantic 18 Function 'add' expects 2 arguments, found 1
// EXPECT: Semantic 19 Argument 1 of 'add': cannot pass float to int parameter 'a'
// EXPECT: Semantic 19 Argument 2 of 'add': cannot pass bool to int parameter 'b'
// EXPECT: Semantic 20 Cannot call 'x': it is a variable, not a function
int add(int a, int b) {
    return a + b;
}
int half(int n) {
    return n / 2.0;
}
int noret(int a) {
    a = a + 1;
}
int main() {
    int x = 1;
    int y = add(1);
    int z = add(1.5, true);
    x(2);
    return x;
}
