// EXPECT: Semantic 6 Cannot assign to function 'f'
int f() {
    return 1;
}
int main() {
    f = 2;
    return 0;
}
