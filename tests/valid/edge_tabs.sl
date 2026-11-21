// EXPECT: OK
// Edge case: tabs for indentation and between tokens (a tab is one column, D-014).
int	add(int	a,	int	b)	{
	int	sum	=	a	+	b;
	if	(sum	>	10)	{
		sum	=	10;
	}
	return	sum;
}

int	main()	{
	return	add(3,	4);
}
