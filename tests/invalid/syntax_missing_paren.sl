// EXPECT: Syntax 4 Expected ')' but found '{'
int main() {
    int a = 1;
    if (a > 0 {
        a = 2;
    }
    return a;
}
