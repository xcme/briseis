#!/usr/local/bin/python
#coding=UTF8

# enter here your nums of metrics for each case
devmetrnums={
    'DES-3028':      {'CNS':24, 'RX_crc':28, '~RX':28, '~TX':28, 'RX':28, 'TX':28, 'P1L*':24, 'P2L/C1*':0,  'P2L*':24, 'P3L/C1*':0,  'DS':28, 'DS*':28, 'DS#':28, 'P1S':24, 'P2S':24, 'P2S/C1':0,  'P3S/C1':0,  'P1L':24, 'P2L':24, 'P2L/C1':0,  'P3L/C1':0,  'UP':1, 'FW':1},
    'DES-3200-18':   {'CNS':16, 'RX_crc':18, '~RX':18, '~TX':18, 'RX':18, 'TX':18, 'P1L*':16, 'P2L/C1*':0,  'P2L*':16, 'P3L/C1*':0,  'DS':18, 'DS*':18, 'DS#':18, 'P1S':16, 'P2S':16, 'P2S/C1':0,  'P3S/C1':0,  'P1L':16, 'P2L':16, 'P2L/C1':0,  'P3L/C1':0,  'UP':1, 'FW':1},
    'DES-3200-18/C1':{'CNS':16, 'RX_crc':18, '~RX':18, '~TX':18, 'RX':18, 'TX':18, 'P1L*':0,  'P2L/C1*':16, 'P2L*':0,  'P3L/C1*':16, 'DS':18, 'DS*':18, 'DS#':18, 'P1S':0,  'P2S':0,  'P2S/C1':16, 'P3S/C1':16, 'P1L':0,  'P2L':0,  'P2L/C1':16, 'P3L/C1':16, 'UP':1, 'FW':1},
    'DES-3200-28':   {'CNS':24, 'RX_crc':28, '~RX':28, '~TX':28, 'RX':28, 'TX':28, 'P1L*':24, 'P2L/C1*':0,  'P2L*':24, 'P3L/C1*':0,  'DS':28, 'DS*':28, 'DS#':28, 'P1S':24, 'P2S':24, 'P2S/C1':0,  'P3S/C1':0,  'P1L':24, 'P2L':24, 'P2L/C1':0,  'P3L/C1':0,  'UP':1, 'FW':1},
    'DES-3200-28/C1':{'CNS':24, 'RX_crc':28, '~RX':28, '~TX':28, 'RX':28, 'TX':28, 'P1L*':0,  'P2L/C1*':24, 'P2L*':0,  'P3L/C1*':24, 'DS':28, 'DS*':28, 'DS#':28, 'P1S':0,  'P2S':0,  'P2S/C1':24, 'P3S/C1':24, 'P1L':0,  'P2L':0,  'P2L/C1':24, 'P3L/C1':24, 'UP':1, 'FW':1},
}


# put here your nums of devices
devtypescnt={
    'DES-3028':10,
    'DES-3200-18':20,
    'DES-3200-18/C1':30,
    'DES-3200-28':40,
    'DES-3200-28/C1':50,
    }

# enter here your metrics for each pass
passes={
    'Pass №1 Total'    :['CNS', 'RX_crc', '~RX', '~TX',                                                   'DS',                                                                                   'UP', 'FW'],
    'Pass №1 Carbon'   :[                                                                                                                                                                                   ],
    'Pass №1 Attractor':['CNS', 'RX_crc',                                                                 'DS', 'DS*', 'DS#',                                                                     'UP', 'FW'],
    'Pass №2 Total'    :['CNS', 'RX_crc', '~RX', '~TX', 'RX', 'TX',                                       'DS',               'P1S', 'P2S', 'P2S/C1', 'P3S/C1', 'P1L', 'P2L', 'P2L/C1', 'P3L/C1', 'UP'      ],
    'Pass №2 Carbon'   :[                               'RX', 'TX',                                                                                                                                         ],
    'Pass №2 Attractor':['CNS', 'RX_crc',                           'P1L*', 'P2L/C1*', 'P2L*', 'P3L/C1*', 'DS', 'DS*', 'DS#', 'P1S', 'P2S', 'P2S/C1', 'P3S/C1', 'P1L', 'P2L', 'P2L/C1', 'P3L/C1', 'UP'      ],
}

# do not modify this dict
devmetrcnt_={
    'DES-3028':0,
    'DES-3200-18':0,
    'DES-3200-18/C1':0,
    'DES-3200-28':0,
    'DES-3200-28/C1':0,
}


for pass_ in sorted(passes.keys()):
    devmetrcnt=devmetrcnt_.copy()
    for dev in devmetrnums:
	for metr in passes[pass_]:
	    if metr in devmetrnums[dev]:
		devmetrcnt[dev] += devmetrnums[dev][metr]
    print devmetrcnt
    totalnum = 0
    for devm in devmetrcnt:
	totalnum += devmetrcnt[devm]*devtypescnt[devm]
    print "{} {}\n".format(pass_, totalnum)
