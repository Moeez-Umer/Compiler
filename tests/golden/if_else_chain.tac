func classify:
  tag = 0
  t1 = n < 0
  ifFalse t1 goto L1
  t2 = - 10
  t3 = n < t2
  ifFalse t3 goto L3
  t4 = - 2
  return t4
L3:
  t5 = - 1
  tag = t5
  goto L2
L1:
  t6 = n == 0
  ifFalse t6 goto L4
  tag = 0
  goto L5
L4:
  t7 = n < 10
  ifFalse t7 goto L6
  tag = 1
  goto L7
L6:
  tag = 2
L7:
L5:
L2:
  return tag
endfunc
