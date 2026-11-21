// EXPECT: Semantic 5 Missing return at end of function 'nothing'
// Edge case: every function returns a value (no void), so an empty body is a semantic error (D-035).
int nothing() {
    int unused = 0;
}
