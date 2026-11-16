// EXPECT: Syntax 4 Expected statement but found 'else'
int main() {
    int a = 1;
    else { a = 2; }
    return a;
}
