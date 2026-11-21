// EXPECT: Semantic 3 Undeclared identifier 'late'
int early() {
    return late;
}
int late = 5;
