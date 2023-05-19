import can
import time
import matplotlib.pyplot as plt
from scipy.stats import rankdata
from math import sqrt
class component:
    def __init__(self, num, id) -> None:
        self.id = id
        self.readings = []
        self.readings_quantised = [0]*num
        self.ranking = [0]*num
        self.is_twos_complement = False
        self.spearman_scores = []
        self.spearman_ids = []
        self.spearman_offset = 0
        self.spearman_mean = 0
        self.spearman_sd = 0
    def sort_spearman(self):
        #<external code>
        # source: stackoverflow: https://stackoverflow.com/questions/9764298/given-parallel-lists-how-can-i-sort-one-while-permuting-rearranging-the-other
        # last accessed: 02/05/2023
        # implementation: sorts spearman_scores by value, and rearranges spearman_ids in same way so that the indices for any pair are always the same
        self.spearman_scores , self.spearman_ids = zip(*sorted(zip(self.spearman_scores, self.spearman_ids)))
        #self.spearman_scores = list(self.spearman_scores)
        #self.spearman_ids = list(self.spearman_ids)
        
        #index = range(len(self.spearman_scores))
        #index = sorted(index, key=self.spearman_scores.__getitem__)
        #map(self.spearman_scores.__getitem__, index)
        #map(self.spearman_ids.__getitem__, index)
        #</external code>





resolution = 0.01 #number of seconds per reading
max_time = 30
num_time_intervals = int(max_time/resolution)

components = {}
id_list = []


t1 = time.time()
t=0
with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
    while t < max_time:
        msg = conn.recv()
        t = time.time() - t1
        if msg.arbitration_id not in components:
            components[msg.arbitration_id] = component(num_time_intervals, msg.arbitration_id)
            id_list += [msg.arbitration_id]
        components[msg.arbitration_id].readings += [[t,msg.data]]
t = time.time() - t1
print("reading complete")
#comp_inputs_quantised = {}
for comp in components:
    readings = components[comp].readings #list of all inputs by one component

    #quantising the inputs by only storing the final input from each section of time, determined by 'resolution'
    inputs_quantised = [0]*int(max_time/resolution)
    has_not_been_changed= [True]*int(max_time/resolution)
    sum_gap = 0
    num_occurences = 0
    last_val=0
    for r in readings:
        index = int(r[0]/resolution)
        num = int(r[1].hex(),16)
        if index < len(inputs_quantised): #sanity check; occasionally there will be a time value greater than max time
            inputs_quantised[index] = num#int(r[1].hex(),16)
            has_not_been_changed[index] = False
        if (num > 127 and last_val <= 127) or (num <=127 and last_val > 127):
            sum_gap += abs(num-last_val)
            num_occurences += 1
        last_val = num
    avg_gap = 0
    if num_occurences:
        avg_gap = sum_gap/num_occurences
        if avg_gap > 150: # 127 + some wiggle room
            components[comp].is_twos_complement = True
    print(f"{components[comp].id}: {avg_gap} {sum_gap} {num_occurences}")

    #filling any 'gaps' in input_quantised by replacing with directly previous value
    #occasionally there will not be an input for each timeframe, more likely the lower 'resolution' is
    has_been_first = False
    last_val = 0
#    sum_gap_num_occurences = [0,0]
    for i in range(0,num_time_intervals): #filling in any gaps in inputs_quantised
#        if (inputs_quantised[i] >= 128 and last_val < 128) or (last_val >= 128 and inputs_quantised[i] < 128):
#            sum_gap_num_occurences[0] += abs(inputs_quantised[i]- last_val)
#            sum_gap_num_occurences[1] += 1
        
        if has_not_been_changed[i]:
            inputs_quantised[i] = last_val
        else:
            last_val = inputs_quantised[i]

        if components[comp].is_twos_complement and inputs_quantised[i] > 127:
            inputs_quantised[i] = inputs_quantised[i] - 256
#        if comp in [0x2, 0x3, 0x5,6,7] and inputs_quantised[i] > 127:
#            inputs_quantised[i] = inputs_quantised[i] - 256
    
    #checking byte encoding - is range of byte 0 -> 255 or -128 -> 127 (using Twos complement)
    #if using twos complement, value going from 0 to -1 will 'jump' from 0 to 255 when read using standard byte encoding
    #therefore, testing avg size of jump from 2 consecutive values where one is below 128 and the other one above 128
    #if the average gap >127, it is likely using twos complement representation (-128->127)
    #if the average gap <127, it is likely not using twos complement (0->255)
    #if it is using twos complement, correct the reading by subtracting 256 from any value >127
#    if sum_gap_num_occurences[0] > 0:
#        avg_gap = sum_gap_num_occurences[0]/sum_gap_num_occurences[1]
#        print(f"{components[comp].id}: {avg_gap} {sum_gap_num_occurences}")
#        if avg_gap > 240: #technically 127 is correct value but add a bit of wiggle room
#            components[comp].is_twos_complement = True
#            for i in range(0,len(inputs_quantised)):
#                if inputs_quantised[i] > 127: 
#                    inputs_quantised[i] = inputs_quantised[i] - 256

    
    components[comp].readings_quantised = inputs_quantised

#calcualting spearmans correlation coefficient for each pair of components
#step one: find the ranking of each input from each component
#example: say component A has set of inputs [0,5,6,3,2,8,9,9]
#                                    r(A) = [1,4,5,3,2,6,7.5,7.5]
mean = (num_time_intervals+1)/2
for comp in components: #calculate rankings
    components[comp].ranking = rankdata(components[comp].readings_quantised, method='average')
    last_val = 0; has_been_dif = True; ties = []
    for r in components[comp].ranking: #checking for ties
        if r == last_val:
            if has_been_dif:
                ties += [1]
            else:
                ties[-1] += 1
            has_been_dif = False
        else:
            last_val = r
            has_been_dif = True
    spearman_offset = 0
    for tie in ties:
        spearman_offset += (tie**3 - tie)/12
    components[comp].spearman_offset = spearman_offset
    #sum = ( float( len( ranking[comp] ) ) / 2)*(len(ranking[comp])+1)
    #mean = (len(ranking[comp])+1)/2
#    sum = 0
#    for i in range(0,len(components[comp].ranking)):
#        sum += (components[comp].ranking[i] - mean)**2
#    components[comp].spearman_sd = sqrt(sum/len(components[comp].ranking))

#calculating spearman coeffient for each pair of components
#spearman_comp_pairs = {}
denominator = (num_time_intervals**3) - num_time_intervals

for i in range(0,len(id_list)):
    for j in range(i+1,len(id_list)): #I need to replace this with some heuristic - double nested for loop is physically painful :(
        diff = 0
#        sum = 0
        for k in range(0,num_time_intervals):
            diff += (components[id_list[i]].ranking[k] - components[id_list[j]].ranking[k])**2
#            sum += (components[id_list[i]].ranking[k] - mean) * (components[id_list[j]].ranking[k] - mean)
#        covariance = sum/num_time_intervals
#        spearman_score = covariance/(components[id_list[i]].spearman_sd * components[id_list[j]].spearman_sd)
        total_sp_offset = components[id_list[i]].spearman_offset + components[id_list[j]].spearman_offset
        spearman_score = 1 - (6*diff + total_sp_offset) / denominator
        #components[id_list[i]].spearman_scores[id_list[j]] = spearman_score
        #components[id_list[j]].spearman_scores[id_list[i]] = spearman_score

        components[id_list[i]].spearman_scores += [spearman_score]
        components[id_list[i]].spearman_ids += [id_list[j]]

        components[id_list[j]].spearman_scores += [spearman_score]
        components[id_list[j]].spearman_ids += [id_list[i]]
        #spearman_comp_pairs[(id_list[i],id_list[j])] = spearman_score
    components[id_list[i]].sort_spearman()
#print(spearman_comp_pairs)

for j in range(0,len(id_list)):
    print(f"---{id_list[j]}---")
    for i in range(0,len(components[id_list[j]].spearman_scores)):
        print(f"{components[id_list[j]].spearman_ids[i]}: {components[id_list[j]].spearman_scores[i]}")
#print(components[1].spearman_scores)
#print(components[1].readings_quantised)

print("-------")
sp_list = []
for comp in components:
    sp_sum = sum(components[comp].spearman_scores)
    sp_list += [[comp.id, sp_sum]]
    print(f"{components[comp].id}: {sp_sum}")
sp_list = sorted(sp_list,key = lambda sp:sp[1], reverse=True)

# get comp with biggest sp_val 
# start recording traffic again
# play minimum value from comp 5 secs, max value from comp 5 secs
# or maybe have it gradually increase from min to max over 10 secs (probably better)
# if it is an input, then the sp_val will remain similar
# if it is an output, the sp_val will be lower
# if it is an input
    #maybe look at the values of other comps?
    # if throttle high
        # abs(vel, wheels) high too
    # if steering high
        # abs(wheels) high too
        # vel probably stays the same
    # if gear:
        # 1 = vel, wheels are positive
        # -1 = vel, wheels are negative

# if it is an output then ...
#   look at what spearman scores have decreased?
#       for wheel:
#           steering, opposite wheel, throttle, gear, avg_vel
#       for vel:
#           wheels, throttle, gear, steering
#   case: one goes from really high to really low:
#       kill me


exit()
#cheaty bit
print("----------------------------------------")
for i in range(0,len(components[1].readings_quantised)):
    if components[3].readings_quantised[i]:
        components[1].readings_quantised[i] = components[1].readings_quantised[i] * components[3].readings_quantised[i]

components[1].ranking = rankdata(components[1].readings_quantised, method='average')
components[1].spearman_scores = []
components[1].spearman_ids = []
for i in range(2,8):
        if i == 4:continue
        diff = 0
        for k in range(0,num_time_intervals):
            diff += (components[1].ranking[k] - components[i].ranking[k])**2
        spearman_score = 1 - (6*diff) / denominator
        #components[id_list[i]].spearman_scores[id_list[j]] = spearman_score
        #components[id_list[j]].spearman_scores[id_list[i]] = spearman_score

        components[1].spearman_scores += [spearman_score]
        components[1].spearman_ids += [i]


for i in range(0,len(components[1].spearman_scores)):
        print(f"{components[1].spearman_ids[i]}: {components[1].spearman_scores[i]}")


#find components with highest absolute spearmans
#likely to be key components
print("-------")
for comp in components:
    print(type(components[comp].spearman_scores))
    sp_sum = sum(components[comp].spearman_scores)
    print(f"{components[comp].id}: {sp_sum}")
#print(components[3].readings_quantised)
#print(len(components[1].ranking))
#print(len(components[5].ranking))
exit()
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
#for comp_pair in spearman_comp_pairs:
#    if spearman_comp_pairs[comp_pair] > initial_threshold - step:
#        pass
biggest_score = 0
biggest_ids = (0,0)
for comp in components:
    sps = components[comp].spearman_scores
    score = sps[-1] + sps[-2]
    if score > biggest_score:
        biggest_score = score
        biggest_ids = (components[comp].spearman_ids[-1], components[comp].spearman_ids[-2])

c1 = components[id_list[0]]
c2 = components[id_list[1]]
closest_to_zero_val = 2
closest_to_zero_ids = (0,0)
for i in range(0,len(c1.spearman_scores)):
    prev_val = 0
    for j in range(len(c2.spearman_scores)-1, -1):
        val = c1.spearman_scores[i] + c2.spearman_scores[j]
        if abs(val) < abs(closest_to_zero_val):
            closest_to_zero_val = val
            closest_to_zero_ids = (i,j)
            if val == 0: break
        #if its no longer getting closer to 0
        if prev_val/val < 0: #negative if they do not have the same sign
            break
        prev_val = val
        

#filter: >= 2 high correlations
#filter: of those correlations, pair that have high correlation with each other
#filter: of those pairs, one has high pos correlation with turning, other has high neg with turning
#identified: avg_vel, left_wheel, right_wheel, turning



#alternative - have list of score with each comp for each comp, sorted highest -> lowest
# identify avg_vel : 2 very high, similar, correlations will be wheels
# look at potential wheel candidates: what is their correlation? find turning by looking for strong correlation, similar size but opposite direction
# once identified potential turning, check with vel; correlation should be close to 0
# having identified all of them, find throttle, brake and gear
plt.plot(components[0x10].readings_quantised, 'b') #throttle
plt.plot(components[0x20].readings_quantised, 'cyan') #steering
plt.plot(components[0x70].readings_quantised, 'r') #left wheel
plt.plot(components[0x80].readings_quantised, 'pink') #right wheel
plt.plot(components[0x90].readings_quantised, 'g') # average velocity
plt.show()

#print(components)
print("hi?")
