// Demo: lexical and syntax errors. The pipeline stops after parsing.
int main() {
    int a = 5 @ 1;
    int b = ;
    int c = 1
    if (a > 0 {
        a = 2;
    }
    return a;
}
