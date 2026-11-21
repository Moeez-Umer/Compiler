// EXPECT: Semantic 6 Function 'one' expects 1 argument, found 2
int one(int a) {
    return a;
}
int main() {
    return one(1, 2);
}
