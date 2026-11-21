globals:
  x = 1
func main:
  x_1 = 2
  x_2 = 3
  t1 = x_2 + 1
  x_2 = t1
  x_3 = 0
L1:
  t2 = x_3 < 2
  ifFalse t2 goto L2
  t1_1 = x_3
  t3 = t1_1 + 1
  L1_1 = t3
  t4 = x_3 + 1
  x_3 = t4
  goto L1
L2:
  return x_1
endfunc
