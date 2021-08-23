#include <stdio.h>
#include <unistd.h>
#include <limits.h>

void function3() {
    char c[] = "Third functioncall memory.";
    int i = 0;
    for (i = 0; i < INT_MAX; i++){}
}

void function2() {
    char c[] = "Second function call memory.";
    function3();
}

void function1() {
    char c[] = "First function call memory.";
    function2();
}

int main() {
    char c[] = "Main function call memory.";
    while(1) {
        function1();
    }
}
