globals:
  PI = 3.14
  NEWLINE = '\n'
  t1 = ! false
  START_FLAG = t1
func main:
  t2 = - PI
  f = t2
  t3 = - 5
  t4 = - t3
  neg = t4
  ch = 'a'
  b = true
  t5 = ! b
  t6 = ! t5
  flipped = t6
  t7 = flipped && START_FLAG
  ifFalse t7 goto L1
  t8 = neg + ch
  uninitLocal = t8
  goto L2
L1:
  uninitLocal = 0
L2:
  return uninitLocal
endfunc
