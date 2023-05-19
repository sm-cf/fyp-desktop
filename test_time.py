import time

def schedule_times(max_time, res, offset):
    t= time.time()
    ts = [t + offset + res*i for i in range(int(max_time/res))]
    return ts
time.sleep(-1)
a = schedule_times(10,0.5,5)
print(a)
print(len(a))