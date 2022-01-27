define len 150;

__in bit regA[11];
__in bit regB[13];
__in bit regC[15];
__in bit regD[16];
__in bit regE[17];
__out bit output[len];

bit majority(bit a, bit b, bit c, bit d, bit e)
{
	return (a&b&c)^(a&b&d)^(a&b&e)^(a&c&d)^(a&c&e)^(a&d&e)^(b&c&d)^(b&c&e)^(b&d&e)^(c&d&e)^
		(a&b&c&d)^(a&b&c&e)^(a&b&d&e)^(a&c&d&e)^(b&c&d&e);
}
bit shiftRegA(){
	bit x = regA[10];
	bit y = regA[10]^regA[8]^regA[3]^regA[1];
	for(int j = 10; j > 0; j=j-1){
		regA[j] = regA[j-1];
	}
	regA[0] = y;
	return x;
}
bit shiftRegB(){
	bit x = regB[12];
	bit y = regB[12]^regB[3]^regB[2]^regB[0];
	for(int j = 12; j > 0; j=j-1){
		regB[j] = regB[j-1];
	}
	regB[0] = y;
	return x;
}
bit shiftRegC(){
	bit x = regC[14];
	bit y = regC[14]^regC[4]^regC[3]^regC[1];
	for(int j = 14; j > 0; j=j-1){
		regC[j] = regC[j-1];
	}
	regC[0] = y;
	return x;
}
bit shiftRegD(){
	bit x = regD[15];
	bit y = regD[15]^regD[5]^regD[3]^regD[0];
	for(int j = 15; j > 0; j=j-1){
		regD[j] = regD[j-1];
	}
	regD[0] = y;
	return x;
}
bit shiftRegE(){
	bit x = regE[16];
	bit y = regE[16]^regE[5]^regE[3]^regE[1];
	for(int j = 16; j > 0; j=j-1){
		regE[j] = regE[j-1];
	}
	regE[0] = y;
	return x;
}
void main()
{
	for(int i = 0; i < len; i = i + 1)
	{
		output[i] = majority(shiftRegA(),shiftRegB(),shiftRegC(),shiftRegD(),shiftRegE());
	}
}
