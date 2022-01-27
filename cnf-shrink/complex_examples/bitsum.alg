
__in bit reg[1300];
__out bit result;

bit summator[12];


void main()
{
	summator = 0;
	for(int i = 0; i < 1300; i = i + 1)
	{
		summator = summator + reg[i];
	}
        result = summator == 100;
	assert(result);
}
