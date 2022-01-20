// Сортировка вставками
// Массив данных из k чисел
// Размер каждого из этих чисел - 1 байт

define size 10;
define log_size 4;
define n 8;

__in bit data[size][n];

__out bit sorted_data[size][n];

void main()
{
	for(int i = 1; i < size; i = i + 1)
	{
		bit item[n] = data[i];
		bit cond = 1;
		bit index[log_size] = i;
		for(int j = i; j > 0; j = j - 1)
		{
			cond = cond & (data[j - 1] > item);
			if(cond)
			{
				data[j] = data[j - 1];
				index = j - 1;
			}
		}

		for(int k = 0; k < i; k = k + 1)
		{
			if(index == k)
			{
				data[k] = item;
			}
		}

		//bit item[n] = data[i];
		//for(int j = i; j > 0 & data[j - 1] > item; j = j - 1)
		//{
		//	data[j] = data[j - 1];
		//}
		//data[j] = item;
	}

	sorted_data = data;
}
