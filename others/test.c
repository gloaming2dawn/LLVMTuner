#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define f1(x,y,z)	((x & y) | (~x & z))
#define f2(x,y,z)	(x ^ y ^ z)
#define f3(x,y,z)	((x & y) | (x & z) | (y & z))
#define f4(x,y,z)	(x ^ y ^ z)

#define CONST1		0x5a827999L
#define CONST2		0x6ed9eba1L
#define CONST3		0x8f1bbcdcL
#define CONST4		0xca62c1d6L

#define ROT32(x,n)	((x << n) | (x >> (32 - n)))

#define FUNC(n,i)						\
    temp = ROT32(A,5) + f##n(B,C,D) + E + W[i] + CONST##n;	\
    E = D; D = C; C = ROT32(B,30); B = A; A = temp

int main() {
    unsigned int A, B, C, D, E, temp;
    unsigned int W[80];
    int i;

    // 初始化一些假数据
    A = 0x67452301;
    B = 0xEFCDAB89;
    C = 0x98BADCFE;
    D = 0x10325476;
    E = 0xC3D2E1F0;

    // 初始化W数组，通常在实际算法中，W会通过一些预处理计算得到
    for (i = 0; i < 80; ++i) {
        W[i] = i;
    }

    // 处理循环
    for (i = 0; i < 20; ++i) {
        FUNC(1, i);
    }
    for (i = 20; i < 40; ++i) {
        FUNC(2, i);
    }
    for (i = 40; i < 60; ++i) {
        FUNC(3, i);
    }
    for (i = 60; i < 80; ++i) {
        FUNC(4, i);
    }

    // 打印结果
    printf("A = %08x\n", A);
    printf("B = %08x\n", B);
    printf("C = %08x\n", C);
    printf("D = %08x\n", D);
    printf("E = %08x\n", E);

    return 0;
}
