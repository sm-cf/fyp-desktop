target = 200
a = [0,5,12,24,37,46,52,68,71,85,93]
b= [101,115,127,132,146,158,162,179,183,190]

c = {}
for i in range(0,len(a)):
    c[a[i]] = i

for i in range(0,len(b)):
    if b[i] + target in c:
        print(c[b[i]+target])