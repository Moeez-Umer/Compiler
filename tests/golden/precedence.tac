func main:
  a = 10
  b = 3
  c = 2
  t1 = b * c
  t2 = a + t1
  x = t2
  t3 = a - b
  t4 = t3 - c
  y = t4
  t5 = a + b
  t6 = c % 2
  t7 = t6 + 1
  t8 = t5 * t7
  t9 = t8 / 3
  z = t9
  t10 = a > b
  t11 = b <= c
  t12 = t10 && t11
  t13 = a != c
  t14 = b == 3
  t15 = t13 && t14
  t16 = t12 || t15
  ok = t16
  ifFalse ok goto L1
  t17 = x + y
  return t17
L1:
  return z
endfunc
