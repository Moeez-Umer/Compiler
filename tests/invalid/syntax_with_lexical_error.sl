// EXPECT: Lexical 4 Invalid character '@'
// EXPECT: Syntax 5 Expected expression but found ';'
int main() {
    int a = 5 @ 1;
    int b = ;
    return a;
}
