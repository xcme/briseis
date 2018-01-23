# coding=UTF8
# Строчка выше нужна на случай использования Non-ASCII символов, например кириллицы.

ms_RxTx = {
#     RX           .1.3.6.1.2.1.31.1.1.1.6				ifHCInOctets
    '~RX.1'     : '.1.3.6.1.2.1.31.1.1.1.6.1',
    '~RX.2'     : '.1.3.6.1.2.1.31.1.1.1.6.2',
    '~RX.3'     : '.1.3.6.1.2.1.31.1.1.1.6.3',
    '~RX.4'     : '.1.3.6.1.2.1.31.1.1.1.6.4',
    '~RX.5'     : '.1.3.6.1.2.1.31.1.1.1.6.5',
    '~RX.6'     : '.1.3.6.1.2.1.31.1.1.1.6.6',
#     TX           .1.3.6.1.2.1.31.1.1.1.10				ifHCOutOctets
    '~TX.1'     : '.1.3.6.1.2.1.31.1.1.1.10.1',
    '~TX.2'     : '.1.3.6.1.2.1.31.1.1.1.10.2',
    '~TX.3'     : '.1.3.6.1.2.1.31.1.1.1.10.3',
    '~TX.4'     : '.1.3.6.1.2.1.31.1.1.1.10.4',
    '~TX.5'     : '.1.3.6.1.2.1.31.1.1.1.10.5',
    '~TX.6'     : '.1.3.6.1.2.1.31.1.1.1.10.6',
}

ms_DS = {
#    DS            .1.3.6.1.2.1.10.7.2.1.19				dot3StatsDuplexStatus
    'DS.1'      : '.1.3.6.1.2.1.10.7.2.1.19.1',
    'DS.2'      : '.1.3.6.1.2.1.10.7.2.1.19.2',
    'DS.3'      : '.1.3.6.1.2.1.10.7.2.1.19.3',
    'DS.4'      : '.1.3.6.1.2.1.10.7.2.1.19.4',
    'DS.5'      : '.1.3.6.1.2.1.10.7.2.1.19.5',
    'DS.6'      : '.1.3.6.1.2.1.10.7.2.1.19.6',
}

ms_UpTime = {
#    UP            .1.3.6.1.2.1.1.3.0					sysUpTimeInstance
    'UP.'       : '.1.3.6.1.2.1.1.3.0'
}

ms_CNS = {
#    CNS           .1.3.6.1.4.1.171.10.134.1.1.1.13.1.3			sysPortCtrlSpeed
    'CNS..1'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.1.100',
    'CNS..2'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.2.100',
    'CNS..3'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.3.100',
    'CNS..4'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.4.100',
    'CNS..5'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.5.100',
    'CNS..6'    : '.1.3.6.1.4.1.171.10.134.1.1.1.13.1.3.6.101',
}
