import can
import time
import matplotlib.pyplot as plt
from scipy.stats import rankdata
from math import sqrt
from threading import Thread
import random
from numpy import sign

from scipy.stats import kendalltau

from linear_regressions import linear_regressions

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
        has_been_first = False
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
            for r in self.readings_quantised:
                if r > 127: r-=256

def read_can(max_time,num_time_intervals, components={}):
    t=0
    t1 = time.time()
    components = {}
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while t < max_time:
            msg = conn.recv(timeout=5)
            if msg is None:break
            t = time.time() - t1
            if msg.arbitration_id not in components:
                components[msg.arbitration_id] = component(num_time_intervals, msg.arbitration_id)
            components[msg.arbitration_id].readings += [[t,msg.data]]
    return (list(components.keys()), components)

def process(components, id_list,num_time_intervals, resolution,tc_set={}):
    for comp in components:
        components[comp].process_readings(num_time_intervals,resolution)
        if components[comp].id in tc_set:
            components[comp].is_twos_complement = tc_set[components[comp].id]
        components[comp].convert_twos_complement


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
            tau = kendalltau(components[id_list[i]].ranking, components[id_list[j]].ranking,variant='b')
            print(f"{id_list[i]}:{id_list[j]}:tau:{tau}")
            components[id_list[i]].calc_spearman(components[id_list[j]], denominator)
        components[id_list[i]].sort_spearman()
    return (id_list, components)

def send_msg(id, reading_list,max_time=10,time_btw_changes=0.5,pause_btw_msg = 0.001):
    t=time.time()
    next_change = time_btw_changes

    msg_index = random.randrange(0,len(reading_list))
    data = reading_list[msg_index]
    msg = can.Message(arbitration_id=id, data=[0])

    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        print(f"{time.time()} {t} {time.time()-t} {max_time}")
        while time.time()-t < max_time:
            con.send(msg)
            time.sleep(pause_btw_msg)
            if time.time() - t > next_change:
                next_change += time_btw_changes
                msg_index = random.randrange(0,len(reading_list))
                data = reading_list[msg_index]
            
#            if time.time() - t > next_change:
#                next_change += time_btw_changes
#                if is_twos_complement and data == 255:
#                    data = 0
#                elif data < 255:
#                    data += 1
            msg = can.Message(arbitration_id=id, data=[data])
#        con.send(can.Message(arbitration_id=id, data=[0]))

def v2_send_msg(comps, ids, times):
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        for ti in range(0,len(times)):
            sleep_time = times[ti] - time.time()
            if sleep_time>0:time.sleep(sleep_time)

            for id in ids:
                msg_data = comps[id].readings_quantised[ti]
                if msg_data < 0 : msg_data += 256
                con.send(can.Message(arbitration_id=id, data=[msg_data],is_extended_id=False))
    print(f"done sending except: {id}")
            

def spam_msg(id, readings,times):
    index = 0
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        data = readings[index]
        if data < 0: data += 256
        msg = can.Message(arbitration_id=id, data=[data])
        time.sleep(times[0] - time.time())
        while time.time() < times[-1]:
            if time.time() >= times[index]:
                data = readings[index]
                if data < 0: data += 256
                data = 127-(data-128)
                msg = can.Message(arbitration_id=id, data=[data])
                index += 1
            con.send(msg)
            time.sleep(0.01)
    print(f"done spamming: {id}")


def v3_send_msg(comps, ids, times, opp_id):
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        for ti in range(0,len(times)):
            sleep_time = times[ti] - time.time()
            if sleep_time>0:time.sleep(sleep_time)

            for id in ids:
                msg_data = comps[id].readings_quantised[ti]
                if msg_data < 0 : msg_data += 256
                if id == opp_id: msg_data = 127-(msg_data-128)
                con.send(can.Message(arbitration_id=id, data=[msg_data],is_extended_id=False))

def run(resolution=0.01, max_time=10, ids=[],comps={},tc_set = {}, slp=0):
    num_time_intervals = int(max_time/resolution)
    time.sleep(slp)
    id_list, components = read_can(max_time, num_time_intervals, comps)
    id_list, components = process(components,id_list, num_time_intervals, resolution, tc_set=tc_set)
    return id_list, components

def schedule_times(max_time, res, offset):
    t= time.time() + offset
    ts = [t + res*i for i in range(int(max_time/res))]
    return ts


def honestlyfml(id,msgs,max_time,pause):
    mt = max_time + time.time()
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        while time.time() < mt:
            time.sleep(pause)
            msg = can.Message(arbitration_id=id, data=msgs[0], is_extended_id=False)
            con.send(msg)

def get_low_high_vals(comp):
    high = max(comp.readings_quantised)
    low = min(comp.readings_quantised)
    return(low,high)

def final_send_msg(id, val, pause=0.1):
    time.sleep(pause)
    msg = can.Message(arbitration_id=id, data=[val], is_extended_id=False)
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        for _ in range(10):
            con.send(msg)
            time.sleep(pause)
        con.send(can.Message(arbitration_id=id, data=[0], is_extended_id=False))

def listen_for_id(id, max_time):
    vals = []; mt = max_time + time.time()
    with can.Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as con:
        while time.time()<mt:
            msg = con.recv(timeout=5)
            if msg is None: return vals
            if msg.arbitration_id == id:
                vals.append(msg.data)
    return vals


if __name__ == '__main__':
    resolution = 0.05; max_time = 10; num_intervals = int(max_time/resolution)

    id_list, components = run(resolution=resolution,max_time=max_time)

    print("finished recording")
    time.sleep(2)
    for j in range(0,len(id_list)):
        print(f"---{id_list[j]}---")
        for i in range(0,len(components[id_list[j]].spearman)):
            print(f"{components[id_list[j]].spearman[i]}")
    #print(components[1].spearman_scores)
    #print(components[1].readings_quantised)
    twos_complement_dict = {}

 # can probably remove this   
#    for comp in components:
#        twos_complement_dict[components[comp].id] = components[comp].is_twos_complement

    print("-------")
    
    sp_list = []
    for comp in components:
        sp_sum = sum(abs(x[1]) for x in components[comp].spearman)
        sp_list += [[components[comp].id, sp_sum]]
    sp_list = sorted(sp_list,key = lambda sp:abs(sp[1]), reverse=True)
    print(sp_list)


    relations = {}

    for i in range(len(sp_list)):
        comp = components[sp_list[i][0]]
        print(f"running: {comp.id}...")
        id = comp.id
        is_tc = comp.is_twos_complement
        max_val = 127 if is_tc else 255
#        valid_msgs = list(set(comp.readings_quantised))

#       determine dependent vs independent variables
        get_ids = lambda x: [y[0] for y in x]
        threshold = 0.1
        opp_comp_ids = get_ids(comp.spearman)
        print(f"yellow {opp_comp_ids}")
        
        send_thread = Thread(target=final_send_msg,args=(id,max_val))
        send_thread.start()
        id_two, comp_two = read_can(5,10)
        send_thread.join()#this thread finishes 2 seconds before read_can but good practice
        print(comp_two)
        td = {-1:[],0:[],1:[]}
        for i in range(len(opp_comp_ids)):
            print(f"{opp_comp_ids[i]}")
            if abs(comp.spearman[i][1]) < threshold: continue
            print(f"made it: {opp_comp_ids[i]}")
            if opp_comp_ids[i] in comp_two:
                r = max(int(x[1].hex(),16) for x in comp_two[opp_comp_ids[i]].readings)
                print(f"{comp.id}:{opp_comp_ids[i]}:{r}")
                if components[opp_comp_ids[i]].is_twos_complement and r > 127: r-=256
                td[sign(r)].append(opp_comp_ids[i])
        relations[id] = td
    print(relations)
    rel_sizes = [[r, len(relations[r][-1]) + len(relations[r][1])] for r in relations]
    rel_sizes = sorted(rel_sizes,key=lambda r:r[1], reverse=True)

    guesses_comp = {"throttle": rel_sizes[0][0]}
    predicted_readings = {}
    #after identifying throttle, play in addition to the other inputs.
    all_guesses_done = False
    threshold = 0
    while not all_guesses_done:
        th_mul = 0.2
        pred_r = components[guesses_comp["throttle"]].readings_quantised
        predicted_readings["avg_vel"] = linear_regressions["avg_vel"](pred_r,[1]*len(pred_r), th_mul)#[r*th_mul for r in predicted_readings]
        diff_list = []
        for x in components[guesses_comp["throttle"]].spearman:
            if abs(x[1]) < threshold: break #potentially bad - if using gears evenly, correlation between vel and throttle will be low. Although could reduce threshold over successive iterations
            c2_id = x[0]; c2_readings = components[c2_id].readings_quantised
            diff = 0
            for i in range(len(c2_readings)):
                diff += abs( abs(c2_readings[i]) - predicted_readings["avg_vel"][i])
            diff_list.append([c2_id, diff])
        diff_list = sorted(diff_list,key=lambda d:d[1])
        print(f"diff_list: {diff_list}")
        #guess that the comp with lowest diff is avg_vel
        guesses_comp["avg_vel"] = diff_list[0][0]

        print(f"average_vel is: {diff_list[0][0]}\n{components[diff_list[0][0]].spearman}")

        predicted_readings["gear"] = linear_regressions["gear"](components[guesses_comp["avg_vel"]].readings_quantised) #[sign(r) for r in components[guesses_comp["avg_vel"]].readings_quantised]

        for x in components[guesses_comp["avg_vel"]].spearman:
            if abs(x[1]) < threshold: break #potentially bad - if using gears evenly, correlation between vel and throttle will be low. Although could reduce threshold over successive iterations
            c2_id = x[0]; c2_readings = components[c2_id].readings_quantised
            diff = 0
            for i in range(len(c2_readings)):
                diff += abs( abs(c2_readings[i]) - predicted_readings["gear"][i])
            diff_list.append([c2_id, diff])
        diff_list = sorted(diff_list,key=lambda d:d[1])

        guesses_comp["gear"] = diff_list[0][0]


        
        vel_readings = []
        for id in id_list:
            if id in [guesses_comp["throttle"], guesses_comp["gear"], guesses_comp["avg_vel"]]: continue
            
            play_throttle_thread = Thread(target=final_send_msg, args=(guesses_comp["throttle"], 127))
            play_gear_thread = Thread(target=final_send_msg, args=(guesses_comp["gear"],max(components[guesses_comp["gear"]].readings_quantised)))
            play_steering_thread = Thread(target=final_send_msg, args=(id,max(components[id].readings_quantised)))
            play_gear_thread.start(); play_gear_thread.start(); play_steering_thread().start()

            r = listen_for_id(guesses_comp["avg_vel"])
            vel_readings.append( sum(r)/len(r) )

            play_gear_thread.join(); play_gear_thread.join(); play_steering_thread().join()


        predicted_readings["left_wheel"] = linear_regressions["left_wheel"](components[guesses_comp["throttle"]].readings_quantised, components[guesses_comp["gear"]].readings_quantised, )


        #now calculate the lines, and order by smallest standard error.

        # or kist do all of that in the first place. vel_throttle standard error is significantly lower than lw or rw
        break

            #compare c2 readings_quantised to predicted readings