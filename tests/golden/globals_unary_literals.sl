// EXPECT: OK
const float PI = 3.14;
int uninitGlobal;
char NEWLINE = '\n';
bool START_FLAG = !false;

int main() {
    int uninitLocal;
    float f = -PI;
    int neg = - -5;
    char ch = 'a';
    bool b = true;
    bool flipped = !!b;
    if (flipped && START_FLAG) {
        uninitLocal = neg + ch;
    } else {
        uninitLocal = 0;
    }
    return uninitLocal;
}
