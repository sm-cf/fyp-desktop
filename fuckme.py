from can import Bus
import time
import os
help = {1:[], 2:[], 3:[], 4:[], 5:[], 6:[],7:[]}

with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
    t=time.time();mt = 60 + t 
    while t<mt:
        msg = conn.recv()
        t=time.time()
        help[msg.arbitration_id].append([t, msg.data])


res=0.5
intervals = int(60/res)
start_time = mt - 60
help_2 = {1:[], 2:[], 3:[],4:[], 5:[], 6:[],7:[]}
for cmp in help:
    readings = help[cmp]
    inps = [0] * (intervals+1)
    for r in readings:
        ti= r[0] - start_time; 
        index = int(ti/res)
        print(index)
        val  = int(r[1].hex(),16)
        if cmp > 2 and val > 127: val -= 256
        inps[index] = val
    help_2[cmp] = inps





print(help_2)
f = open('data.txt','w')
f.write("1\t2\t3\t4\t5\t6\t7\n")
for i in range(intervals):
    f.write(f"{help_2[1][i]}\t{help_2[2][i]}\t{help_2[3][i]}\t{help_2[4][i]}\t{help_2[5][i]}\t{help_2[6][i]}\t{help_2[7][i]}\n")

f.close()
    

