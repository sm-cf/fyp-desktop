import can
import time
import matplotlib.pyplot as plt
from scipy.stats import rankdata
max_time = 20
inputs = {}
id_list = []
resolution = 0.05
t1 = time.time()
t=0
with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
    while t < max_time:
        msg = conn.recv()
        t = time.time() - t1
        if msg.arbitration_id not in inputs:
            inputs[msg.arbitration_id] = []
            id_list += [msg.arbitration_id]
        inputs[msg.arbitration_id] += [[t,msg.data]]
t = time.time() - t1

comp_inputs_quantised = {}
for comp in inputs:
    data = inputs[comp] #list of all inputs by one component
    print(data)

    #quantising the inputs by only storing the final input from each section of time, determined by 'resolution'
    inputs_quantised = [0]*int(max_time/resolution)
    has_not_been_changed= [True]*int(max_time/resolution)
    for inp in data:
        index = int(inp[0]/resolution)
        if index < len(inputs_quantised): #sanity check; occasionally there will be a time value greater than max time
            print(inp[1])
            inputs_quantised[index] = int(inp[1].hex(),16)
            has_not_been_changed[index] = False

    #filling any 'gaps' in input_quantised by replacing with directly previous value
    #occasionally there will not be an input for each timeframe, more likely the lower 'resolution' is
    has_been_first = False
    last_val = 0
    sum_gap_num_occurences = (0,0)
    for i in range(0,len(has_not_been_changed)): #filling in any gaps in inputs_quantised
        if (inputs_quantised[i] >= 128 and last_val < 128) or (last_val >= 128 and inputs_quantised[i] < 128):
            sum_gap_num_occurences[0] += abs(inputs_quantised[i]- last_val)
            sum_gap_num_occurences[1] += 1
        
        if has_not_been_changed[i]:
            inputs_quantised[i] = last_val
        else:
            last_val = inputs_quantised[i]
        #if comp in [0x20, 0x70, 0x80, 0x90] and inputs_quantised[i] > 127:
        #    inputs_quantised[i] = inputs_quantised[i] - 256
    
    #checking byte encoding - is range of byte 0 -> 255 or -128 -> 127 (using Twos complement)
    #if using twos complement, value going from 0 to -1 will 'jump' from 0 to 255 when read using standard byte encoding
    #therefore, testing avg size of jump from 2 consecutive values where one is below 128 and the other one above 128
    #if the average gap >127, it is likely using twos complement representation (-128->127)
    #if the average gap <127, it is likely not using twos complement (0->255)
    #if it is using twos complement, correct the reading by subtracting 256 from any value >127
    if not sum_gap_num_occurences[0]:
        avg_gap = sum_gap_num_occurences[0]/sum_gap_num_occurences[1]
        if avg_gap > 127:
            for i in range(0,len(inputs_quantised)):
                if inputs_quantised[i] > 127: 
                    inputs_quantised[i] = inputs_quantised[i] - 256
    
    comp_inputs_quantised[comp] = inputs_quantised

#calcualting spearmans correlation coefficient for each pair of components
#step one: find the ranking of each input from each component
#example: say component A has set of inputs [0,5,6,3,2,8,9,9]
#                                    r(A) = [1,4,5,3,2,6,7.5,7.5]
ranking = {}
for comp in comp_inputs_quantised:
    ranking[comp] = rankdata(comp_inputs_quantised[comp],method='average') #calculate rankings
    #sum = ( float( len( ranking[comp] ) ) / 2)*(len(ranking[comp])+1)
    #mean = (len(ranking[comp])+1)/2

#calculating spearman coeffient for each pair of components
spearman_comp_pairs = {}
for i in range(0,len(id_list)):
    for j in range(i+1,len(id_list)): #I need to replace this with some heuristic - double nested for loop is physically painful :(
        diff = 0
        for k in range(0,len(comp_inputs_quantised[id_list[i]])):
            diff += (ranking[id_list[i]][k] - ranking[id_list[j]][k]) ** 2
        spearman_score = 1 - (6*diff) / ( (len(comp_inputs_quantised[id_list[i]])**3) - len(comp_inputs_quantised[id_list[i]]))
        spearman_comp_pairs[(id_list[i],id_list[j])] = spearman_score

print(spearman_comp_pairs)
#what components do we expect to have high coeffient?
# throttle - avg velocity (strong pos/neg)   NB: depends how much time forward vs reverse
# throttle - wheels       (mid/weak pos/neg) NB: depends how much time forward vs reverse
# avg velocity - wheels   (strong pos) 
# turning - left wheel    (strong pos)
# turning - right wheel   (strong neg)
# left wheel - right wheel (mid pos)
# gear    - avg velocity  (strong pos)
# brake   - avg velocity  (weak neg) 

# improve throttle - wheels by incorporating gear, brake
# look for gear such that gear * throttle improves throttle - vel
# look for brake such that throttle - brake improves throttle - vel

# step one:
# identifying the unique vel - lw - rw - steering relation
# search for avg vel
# will have high correlation with left wheel, right wheel
# neutral? with steering
# steering will have high pos correlation with right wheel, neg left wheel
initial_threshold = 1
step = 0.05
for comp_pair in spearman_comp_pairs:
    if spearman_comp_pairs[comp_pair] > initial_threshold - step:
        pass
#alternative - have list of score with each comp for each comp, sorted highest -> lowest
# identify avg_vel : 2 very high, similar, correlations will be wheels
# look at potential wheel candidates: what is their correlation? find turning by looking for strong correlation, similar size but opposite direction
# once identified potential turning, check with vel; correlation should be close to 0
# having identified all of them, find throttle, brake and gear
plt.plot(comp_inputs_quantised[0x10], 'b') #throttle
plt.plot(comp_inputs_quantised[0x20], 'cyan') #steering
plt.plot(comp_inputs_quantised[0x70], 'r') #left wheel
plt.plot(comp_inputs_quantised[0x80], 'pink') #right wheel
plt.plot(comp_inputs_quantised[0x90], 'g') # average velocity
plt.show()

print(comp_inputs_quantised)
print("hi?")

#quantising the inputs
exit()
ti = 0
index_data = 0
index_inputs = 0
while ti < t:
    ti += resolution
    while index_data < len(data):
        if data[index_data][0] < ti:
            inputs_quantised[index_inputs] = data[index_data][1]
        index_data+=1
    index_inputs +=1
    


#quantise everything
#then standardise it so numpy can be efficient???