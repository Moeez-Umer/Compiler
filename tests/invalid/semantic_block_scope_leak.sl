// EXPECT: Semantic 6 Undeclared identifier 'inner'
int main() {
    {
        int inner = 1;
    }
    inner = 2;
    return 0;
}
