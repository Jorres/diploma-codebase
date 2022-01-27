__in bit a[8];
__in bit b[8];

__out bit result[16];

void main()
{
	result = a * b;
	assert(a < b);
}
