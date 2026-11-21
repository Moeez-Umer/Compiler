func inc:
  t1 = x + 1
  return t1
endfunc
func combine:
  t2 = a * 10
  t3 = t2 + b
  return t3
endfunc
func factorial:
  t4 = n <= 1
  ifFalse t4 goto L1
  return 1
L1:
  t5 = n - 1
  param t5
  t6 = call factorial, 1
  t7 = n * t6
  return t7
endfunc
func main:
  a_1 = 2
  b_1 = 3
  param a_1
  call inc, 1
  param b_1
  t8 = call inc, 1
  param a_1
  param t8
  t9 = call combine, 2
  y = t9
  param 4
  t10 = call factorial, 1
  f = t10
  t11 = y + f
  return t11
endfunc
