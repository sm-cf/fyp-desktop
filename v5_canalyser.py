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


def do_linear_regression(id_list, components, predicted, spearman_threshold=0.2 ):

    sum_diff=[]
    for id in id_list: 
        #id, val = components[comp].spearman[i]
        #if abs(val) < spearman_threshold:continue

        readings = components[id].readings_quantised
        #print(readings)
        sum_diff.append( [ id, sum( abs(readings[i] - predicted[i]) for i in range(len(readings)))    ] )
    print(f"sum_diff: {sum_diff}")
    sum_diff = sorted(sum_diff, key=lambda s:s[1])
    return sum_diff


def v2_linear_regression(guess, id_list, components, prev_guesses, spearman_threshold=0.1):
    
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
    
    
    prediction_args = [components[id].readings_quantised for id in independent_ids]
    prediction = linear_regressions[guess](*prediction_args)
    sum_diff = []
    for id in id_list:
        if components[id] not in spearman_dict: continue
        read = components[id].readings_quantised
        sum_diff.append( [id, sum ( abs( read[r] - prediction[r] ) for r in range(len(read))) ])
        #calculating sum of the differences
    sum_diff = sorted(sum_diff,key=lambda s:s[1])
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
    sp_list = sorted(sp_list,key = lambda sp:abs(sp[1]), reverse=True)
    print(sp_list)

    guesses = {"avg_vel":sp_list[0][0]}#, "gear":-1, "throttle":-1,"brake":-1,"steering":-1,"left_wheel":-1,"right_wheel":-1}

    guesses["avg_vel"] = 7
    id_list = [s[0] for s in components[guesses["avg_vel"]].spearman]

    for r in regression_order:
        sum_diff = v2_linear_regression(r, id_list, components, guesses)
        guesses[r] = sum_diff[0][0]
        id_list.remove(guesses[r])
    print(guesses)
    exit()

    spearman_threshold = 0.2

    prediction = linear_regressions["gear"](components[guesses["avg_vel"]].readings_quantised)
    diff_list = do_linear_regression(id_list, components, prediction)

    print(diff_list)
    guesses["gear"] = diff_list[0][0]
    id_list.remove(guesses["gear"]) # maybe dont do this? Instead, if this comp matches another LR in future then replace it?

    prediction = linear_regressions["throttle"](components[guesses["avg_vel"]].readings_quantised,components[guesses["gear"]].readings_quantised)
    diff_list = do_linear_regression(id_list ,components,prediction)
    print(diff_list)


    guesses["throttle"] = diff_list[0][0]
    id_list.remove(guesses["throttle"])

    prediction = linear_regressions["brake"](components[guesses["avg_vel"]].readings_quantised,components[guesses["throttle"]].readings_quantised, components[guesses["gear"]].readings_quantised)
    diff_list = do_linear_regression(id_list,components,prediction)
    guesses["brake"] = diff_list[0][0]
    id_list.remove(guesses["brake"])
    print(diff_list)

    prediction = linear_regressions["steering"](components[guesses["left_wheel"]].readings_quantised,components[guesses["right_wheel"]].readings_quantised)
    diff_list = do_linear_regression(id_list,components,prediction)
    print(diff_list)
    guesses["steering"] = diff_list[0][0]
    id_list.remove(guesses["steering"])
    #can do this shit in a loop but whatever, will fix in a bit
    #need method for evaluating how good solution is
    #maybe total sum of sum_diff?? if over a certain amount, try again?
    # also how the fuck do you find steering
    # and brake also 

    

    print(guesses)

        


