from numpy import sign
linear_regressions = {
    "avg_vel": lambda throttle,gear,brake: [0.93*(throttle[i]-brake[i])*gear[i] for i in range(len(throttle))],
    "left_wheel": lambda throttle,gear,steering,brake: [0.5*(throttle[i]-brake[i])* gear[i] + 0.4*steering[i] for i in range(len(steering))], #0.5 , 0.4 if brake, 0.4 0.4 if no brake
    "right_wheel": lambda throttle,gear, steering,brake: [0.45*(throttle[i]-brake[i])*gear[i] - 0.4*steering[i] for i in range(len(steering))], #0.45, -0.4 if brake,  0.36 -0.4 if no brake




    "gear": lambda vel: [sign(v) for v in vel],
    "throttle": lambda vel,gear: [vel[i]*gear[i] for i in range(len(vel))],
    "brake": lambda vel, throttle, gear: [0.5*throttle[i]*gear[i]-0.5*vel[i] for i in range(len(vel))],#[abs(5*vel[i]/(throttle[i]*gear[i])) for i in range(len(vel))]
    #"left_wheel": lambda vel: vel,
    #"right_wheel": lambda vel: vel,
    "steering": lambda left_wheel, right_wheel: [0.9* (left_wheel[i] - right_wheel[i]) for i in range(len(left_wheel))]

}

contributing_factors = {
    "avg_vel" : ["throttle","gear","brake"], #order of components in list must be the same as args in linear_regressions
    "left_wheel":["throttle","gear","steering","brake"],
    "right_wheel":["throttle","gear","steering","brake"],
    "gear":["avg_vel"],
    "throttle":["avg_vel","gear"],
    "brake":["avg_vel","throttle","gear"],
    "steering":["left_wheel","right_wheel"]
}

regression_order = ["gear","throttle","brake","left_wheel","right_wheel","steering"]
#th_mul=0.2
#st_mul = 0.36