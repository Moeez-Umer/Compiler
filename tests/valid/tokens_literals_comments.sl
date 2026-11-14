// EXPECT: OK
// Token-level sample: literals, escapes and both comment styles.
/* a block comment
   over several lines, with symbols @ # $ that must be ignored */
const int LIMIT = 100;
const float RATE = 0.5;

int main() {
    char a = 'a';
    char nl = '\n';
    char tab = '\t';
    char slash = '\\';
    char quote = '\'';
    char zero = '\0';
    float pi = 3.14;
    int big = 007; /* inline comment */
    bool yes = true;
    bool no = false;
    return big;
}
