globals:
  LIMIT = 10
func square:
  t1 = x * x
  return t1
endfunc
func sumSquares:
  total = 0
  i = 1
L1:
  t2 = i <= n
  ifFalse t2 goto L2
  param i
  t3 = call square, 1
  t4 = total + t3
  total = t4
  t5 = i + 1
  i = t5
  goto L1
L2:
  return total
endfunc
func average:
  t6 = a + b
  s = t6
  t7 = s / 2
  return t7
endfunc
func main:
  param LIMIT
  t8 = call sumSquares, 1
  r = t8
  t9 = r > 100
  t10 = LIMIT != 0
  t11 = t9 && t10
  big = t11
  ifFalse big goto L3
  t12 = r - 1
  r = t12
  goto L4
L3:
  t13 = r == 0
  ifFalse t13 goto L5
  r = 1
  goto L6
L5:
  r = 0
L6:
L4:
  k = 0
L7:
  t14 = k < 3
  ifFalse t14 goto L8
  t15 = r + k
  r = t15
  t16 = k + 1
  k = t16
  goto L7
L8:
  return r
endfunc
