import can
import time
import matplotlib.pyplot as plt
from scipy.stats import rankdata
from math import sqrt
from threading import Thread
import random
from numpy import sign


from linear_regressions import linear_regressions, contributing_factors, regression_order

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
        self.spearman = []
    def sort_spearman(self):
        self.spearman = sorted(self.spearman, key=lambda s:abs(s[1]), reverse=True)

    def calc_spearman(self, comp, denominator):
        diff = 0
        for k in range(0,len(self.ranking)):
            diff += (self.ranking[k] - comp.ranking[k])**2
        total_sp_offset = self.spearman_offset + comp.spearman_offset
        spearman_score = 1 - (6*diff + total_sp_offset) / denominator
        
#        self.spearman_scores += [spearman_score]
#        self.spearman_ids += [comp.id]

#        comp.spearman_scores += [spearman_score]
#        comp.spearman_ids += [self.id]
        self.spearman.append([comp.id, spearman_score])
        comp.spearman.append([self.id, spearman_score])

    
    def calc_ranking(self):
        self.ranking = rankdata(self.readings_quantised, method='average')
        self.calc_spearman_offset()
    
    def calc_spearman_offset(self):
        last_val = 0; has_been_dif = True; ties = []; spearman_offset = 0
        for r in self.ranking: #checking for ties
            if r == last_val:
                if has_been_dif:
                    ties += [1]
                else:
                    ties[-1] += 1
                has_been_dif = False
            else:
                last_val = r
                has_been_dif = True
        for tie in ties:
            spearman_offset += (tie**3 - tie)/12
        self.spearman_offset = spearman_offset

    def process_readings(self, num_time_intervals, resolution):
        #quantising the inputs by only storing the final input from each section of time, determined by 'resolution'
        inputs_quantised = [0]*num_time_intervals
        has_not_been_changed= [True]*num_time_intervals
        sum_gap = 0
        num_occurences = 0
        last_val=0
        for r in self.readings:
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
                self.is_twos_complement = True
        print(f"{self.id}: {avg_gap} {sum_gap} {num_occurences}")

        #filling any 'gaps' in input_quantised by replacing with directly previous value
        #occasionally there will not be an input for each timeframe, more likely the lower 'resolution' is
        last_val = 0
        for i in range(0,num_time_intervals): #filling in any gaps in inputs_quantised
            if has_not_been_changed[i]:
                inputs_quantised[i] = last_val
            else:
                last_val = inputs_quantised[i]

#            if self.is_twos_complement and inputs_quantised[i] > 127:
#                inputs_quantised[i] = inputs_quantised[i] - 256
        
        #checking byte encoding - is range of byte 0 -> 255 or -128 -> 127 (using Twos complement)
        #if using twos complement, value going from 0 to -1 will 'jump' from 0 to 255 when read using standard byte encoding
        #therefore, testing avg size of jump from 2 consecutive values where one is below 128 and the other one above 128
        #if the average gap >127, it is likely using twos complement representation (-128->127)
        #if the average gap <127, it is likely not using twos complement (0->255)
        #if it is using twos complement, correct the reading by subtracting 256 from any value >127
        
        self.readings_quantised = inputs_quantised

    def convert_twos_complement(self):
        if self.is_twos_complement:
            for i in range(len(self.readings_quantised)):
                if self.readings_quantised[i] > 127:
                    self.readings_quantised[i] -= 256
                
    def normalise(self):
        max_reading = max(self.readings_quantised)
        self.readings_quantised = [r/max_reading for r in self.readings_quantised]

def read_can(max_time,num_time_intervals, components={}):
    t=0
    components = {}
    start_time = time.time()
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while t < max_time:
            msg = conn.recv(timeout=5)
            if msg is None:break
            t = time.time() -start_time
            if msg.arbitration_id not in components:
                components[msg.arbitration_id] = component(num_time_intervals, msg.arbitration_id)
            components[msg.arbitration_id].readings += [[t,msg.data]]
    return (list(components.keys()), components)

def process(components, id_list,num_time_intervals, resolution):
    for comp in components:
        components[comp].process_readings(num_time_intervals,resolution)
        components[comp].convert_twos_complement()


    #calcualting spearmans correlation coefficient for each pair of components
    #step one: find the ranking of each input from each component
    #example: say component A has set of inputs [0,5,6,3,2,8,9,9]
    #                                    r(A) = [1,4,5,3,2,6,7.5,7.5]
    for comp in components: #calculate rankings
        components[comp].calc_ranking()

    #calculating spearman coeffient for each pair of components
    #spearman_comp_pairs = {}
    denominator = (num_time_intervals**3) - num_time_intervals

    for i in range(0,len(id_list)):
        for j in range(i+1,len(id_list)): #I need to replace this with some heuristic - double nested for loop is physically painful :(
            components[id_list[i]].calc_spearman(components[id_list[j]], denominator)
        components[id_list[i]].sort_spearman()
    return (id_list, components)

def run(resolution=0.01, max_time=10, ids=[],comps={},tc_set = {}, slp=0):
    num_time_intervals = int(max_time/resolution)
    time.sleep(slp)
    id_list, components = read_can(max_time, num_time_intervals, comps)
    id_list, components = process(components,id_list, num_time_intervals, resolution)
    return id_list, components


def do_linear_regression(guess, id_list, components, prev_guesses, spearman_threshold=0.0):
    
    independents = contributing_factors[guess]

    independent_ids = [prev_guesses[v] for v in independents]
    spearman_dict = {}
    for indy in independent_ids:
        spearman = components[indy].spearman
        for s in spearman:
            if abs(s[1]) < spearman_threshold: break
            if s[0] not in spearman_dict:
                spearman_dict[s[0]] = []
            spearman_dict[s[0]].append(s[1])
    #now we have a dict of spearman scores for all guesses of contributing factors
    #print(spearman_dict)
    
    prediction_args = [components[id].readings_quantised for id in independent_ids]
    prediction = linear_regressions[guess](*prediction_args)
    sum_diff = []
    for id in id_list:
        #print(f"id: {id}")
        if id not in spearman_dict: continue
        read = components[id].readings_quantised
        sum_diff.append( [id, sum ( abs( read[r] - prediction[r] ) for r in range(len(read))) ])
        #calculating sum of the differences
    sum_diff = sorted(sum_diff,key=lambda s:s[1],reverse=True)
    return sum_diff

        


if __name__ == '__main__':
    resolution = 0.05; max_time = 30; num_intervals = int(max_time/resolution)

    id_list, components = run(resolution=resolution,max_time=max_time)

    print("finished recording")
    for j in range(0,len(id_list)):
        components[id_list[j]].normalise()
        print(f"---{id_list[j]}---")
        for i in range(0,len(components[id_list[j]].spearman)):
            print(f"{components[id_list[j]].spearman[i]}")

    print("-------")
    

    sp_list = []
    for comp in components:
        sp_sum = sum(abs(x[1]) for x in components[comp].spearman)
        sp_list += [[components[comp].id, sp_sum]]
    sp_list = sorted(sp_list,key = lambda sp:abs(sp[1]), reverse=False)
    print(sp_list)

    solutions = {"avg_vel": [sp[0] for sp in sp_list], "gear":[], "throttle":[],"brake":[],"steering":[],"left_wheel":[],"right_wheel":[]}
    threshold = 0.35 * num_intervals #multiplying once is easier than dividing every time
    while len(solutions["avg_vel"]) > 0: # remove if not working :(
        id_list= [s[0] for s in sp_list]
        id_list.remove(solutions["avg_vel"][-1])
        num_loops = len(regression_order); i=0
        while i < num_loops:
            prev_guess = {}
            for s in solutions:
                if solutions[s] == []: continue
                prev_guess[s] = solutions[s][-1]

            sum_diff = do_linear_regression(regression_order[i], id_list, components,prev_guess)
            print(f"{i}: {sum_diff}")
            for sd in sum_diff:
                if sd[1] < threshold:
                    solutions[regression_order[i]].append(sd[0])
        
            if len(solutions[regression_order[i]])>0:
                id_list.remove(solutions[regression_order[i]][-1])
                i+=1

            else:            
                while solutions[regression_order[i]] == []:
                    if i > 0:
                        incorrect = solutions[regression_order[i-1]].pop()
                        id_list.append(incorrect)
                    if i == 0 and solutions[regression_order[i]] == []:
                        incorrect = solutions["avg_vel"].pop()
                        id_list.append(incorrect)
                        break
                    elif solutions[regression_order[i-1]] == []:
                     i-=1
                    else: break

    print(solutions)
    guesses = {}
    for s in solutions:
        if solutions[s] == []: continue
        guesses[s] = solutions[s][-1]
            

    spearman = components[guesses["avg_vel"]].spearman
    wheel1= 0; wheel2=0
    for s in spearman:
        if wheel2 and wheel1: break
        if s[0] in id_list:
            if wheel2:
                wheel1 = s[0]
            else:
                wheel2 = s[0]
        else:continue
        
    guesses["left_wheel"] = wheel1
    guesses["right_wheel"] = wheel2

    id_list.remove(wheel1); id_list.remove(wheel2)
    wheel1_spearman_ids = [s[0] for s in components[wheel1].spearman]
    wheel2_spearman_ids = [s[0] for s in components[wheel2].spearman]

    print(f"wheel1: {wheel1_spearman_ids}")
    print(f"wheel1: {wheel2_spearman_ids}")
    diff = []
    for id in id_list:
        w1_index = wheel1_spearman_ids.index(id)
        w1_val = components[wheel1].spearman[w1_index]
        w2_index = wheel2_spearman_ids.index(id)
        w2_val = components[wheel2].spearman[w2_index]
            
        d = abs(w1_val[1] -w2_val[1])
            
        diff.append(id,d,w1_val[1], w2_val[1])
    diff = sorted(diff, key=lambda d:d[1],reverse=True)
    biggest_diff = diff[0]
    print(f"biggest_diff: {biggest_diff}")
    guesses["steering"] = biggest_diff[0]
    if biggest_diff[2] > biggest_diff[3]:
        guesses["left_wheel"] = wheel1
        guesses["right_wheel"] = wheel2
    else:
        guesses["right_wheel"] = wheel2
        guesses["left_wheel"] = wheel1

        # if sum(sum_diff)  < 1000: break, or something
    #break
    print(guesses)

    exit()

        


