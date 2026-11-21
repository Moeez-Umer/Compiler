func main:
  total = 0
  i = 0
L1:
  t1 = i < 3
  ifFalse t1 goto L2
  j = 0
L3:
  t2 = j < 2
  ifFalse t2 goto L4
  t3 = i == j
  ifFalse t3 goto L5
  t4 = total + 10
  total = t4
  goto L6
L5:
  t5 = total + 1
  total = t5
L6:
  t6 = j + 1
  j = t6
  goto L3
L4:
  t7 = i + 1
  i = t7
  goto L1
L2:
  return total
endfunc
