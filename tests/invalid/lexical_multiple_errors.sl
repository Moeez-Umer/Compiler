// EXPECT: Lexical 5 Malformed number
// EXPECT: Lexical 6 Invalid character '#'
// EXPECT: Lexical 7 Invalid character '&'
int main() {
    float a = 1.2.3;
    int b = 4 # 2;
    bool c = true & false;
    return 0;
}
