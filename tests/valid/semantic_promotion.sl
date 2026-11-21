// EXPECT: OK
// Typing rules: char promotion, mixed int/float, % on int and char, bool operators, all assignable pairs.
int main() {
    char c = 'a';
    int i = c + 1;
    float f = i * 2.5;
    float g = c;
    char d = c;
    int r = c % i + i % 3;
    bool b = i < f && c != d || !(f >= g);
    bool e = b == true;
    int neg = -c;
    float nf = -f;
    bool same = i == f;
    if (b && e) {
        i = r;
    }
    return neg;
}
