// EXPECT: Syntax 6 Expected expression but found ';'
// EXPECT: Syntax 8 Expected expression but found '*'
// EXPECT: Syntax 13 Expected ';' but found 'if'
// EXPECT: Syntax 13 Expected ')' but found '{'
// EXPECT: Syntax 16 Expected statement but found 'else'
int g = ;
int add(int a, int b) {
    int s = a + * b;
    return s;
}
int main() {
    int x = 1
    if (x > 0 {
        x = 2;
    }
    else {
        x = 3;
    }
    return add(x, 4);
}
