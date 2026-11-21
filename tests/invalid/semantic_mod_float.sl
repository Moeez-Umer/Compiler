// EXPECT: Semantic 4 Operator '%' requires int or char operands, found float and int
int main() {
    float f = 1.5;
    int r = f % 2;
    return r;
}
