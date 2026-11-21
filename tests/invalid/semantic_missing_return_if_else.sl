// EXPECT: Semantic 9 Missing return at end of function 'f'
// D-035: strict SPEC rule, both branches return but the LAST statement is not a return.
int f(bool b) {
    if (b) {
        return 1;
    } else {
        return 2;
    }
}
