// Every lexical error kind, one per line (Phase 1 sample).
int main() {
    int a = 5 @ 1;
    bool b = true & false;
    bool c = true | false;
    float d = 3.4.5;
    float e = 3.;
    float f = .5;
    int g = 9abc;
    char h = 'a;
    char i = '';
    char j = 'ab';
    char k = '\q';
    int ok = 42;
    /* this block comment is never closed
    return ok;
}
