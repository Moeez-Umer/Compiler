func findThreshold:
  acc = 1
  step = 0
L1:
  t1 = step < 10
  ifFalse t1 goto L2
  t2 = acc * 2
  acc = t2
  t3 = acc >= limit
  ifFalse t3 goto L3
  return acc
L3:
  t4 = step + 1
  step = t4
  goto L1
L2:
  return acc
endfunc
