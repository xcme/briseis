from userdict import *

#[SNMP]
# SNMP write-community
snmp_WComm    = "private"
# Timeout in microseconds
snmp_Timeout  = 300000
# "Retries = 1" means that all will be sended 2 queries
snmp_Retries  = 2

# Threads
max_processes          = 4
max_devices_in_process = 3500
max_threads            = 8
max_requests_in_thread = 12

# Params
logfile = "/usr/local/etc/briseis/briseis.log"
ModelNameRemoveStr=[
    'D-Link ',
    ' Fast Ethernet Switch',
]
query_interval = 300
sleep_interval = 1
sleep_after_set_requests = 3
try_fix_query_errors = 1

# MySQL
mysql_addr  = "mysql.localhost"
mysql_user  = "user"
mysql_pass  = "password"
mysql_base  = "devices"

# MySQL-query
mysql_query_p = """SELECT deviceid AS id, ip, community AS wcomm FROM devices.devices;"""

useMySQLstat = False
mysql_stat_addr = "attractor.localhost"
mysql_stat_user = "briseis"
mysql_stat_pass = "briseis_pass"
mysql_stat_base = "blackhole"
mysql_stat_cset = "utf8"
mysql_stat_tabl = "stats"

# Graphite
useGraphite = False
GraphiteCarbonAddress = "graphite.localhost"
GraphiteCarbonPort = 2003
GraphiteMetricsList =  ['RX','TX']
GraphiteCarbonPrefix = "sw."

# Attractor
useAttractor = False
AttractorAddress = "attractor.localhost"
AttractorPort = 1907
AttractorMetricsList = ['CNS','RX_crc',          'DS','P1S','P2S','P2S/C1','P3S/C1','P1L','P2L','P2L/C1','P3L/C1','UP','FW']
AttractorDupMetric = {'P1L':['P1L*'],'P2L':['P2L*'],'P2L/C1':['P2L/C1*'],'P3L/C1':['P3L/C1*'],'DS':['DS*','DS#']}

PassSetSet  = {      1:[],
		     2:[],}
#		     2:['InitCableDiag'],}

PassSetWalk = {      1:['CNS','RX_crc','RX','TX','DS',                                                            'UP','FW'],
		     2:['CNS','RX_crc','RX','TX','DS',                                                            'UP',    ],}
#		     2:['CNS','RX_crc','RX','TX','DS','P1S','P2S','P2S/C1','P3S/C1','P1L','P2L','P2L/C1','P3L/C1','UP',    ],}

# OIDs
oid_ModelName = ".1.3.6.1.2.1.1.1.0"


oids_set={
    'DES-3200-28':{
	'InitCableDiag':InitCableDiag24
    },
    'DES-3200-18':{
	'InitCableDiag':InitCableDiag16
    },
    'DES-3200-28/C1':{
	'InitCableDiag':InitCableDiag24
    },
    'DES-3200-18/C1':{
	'InitCableDiag':InitCableDiag16
    },
    'DES-3028':{
	'InitCableDiag':InitCableDiag24
    }
}


oids_walk=[{
    'DES-3200-28':CNS_3200_28,
    'DES-3200-18':CNS_3200_18,
    'DES-3200-28/C1':CNS_3200_28C1,
    'DES-3200-18/C1':CNS_3200_18C1,
    'DES-3028':CNS_3028,
},
    {
    'DES-3200-28':Errors28,
    'DES-3200-18':Errors18,
    'DES-3200-28/C1':Errors28,
    'DES-3200-18/C1':Errors18,
    'DES-3028':Errors28,
},
    {
    'DES-3200-28':RxTx28,
    'DES-3200-18':RxTx18,
    'DES-3200-28/C1':RxTx28,
    'DES-3200-18/C1':RxTx18,
    'DES-3028':RxTx28,
},
    {
    'DES-3200-28':DuplexStatus28,
    'DES-3200-18':DuplexStatus18,
    'DES-3200-28/C1':DuplexStatus28,
    'DES-3200-18/C1':DuplexStatus18,
    'DES-3028':DuplexStatus28,
},
    {
    'DES-3200-28':CableDiagPS24,
    'DES-3200-18':CableDiagPS16,
    'DES-3200-28/C1':CableDiagPS24_C1,
    'DES-3200-18/C1':CableDiagPS16_C1,
    'DES-3028':CableDiagPS24,
},
    {
    'DES-3200-28':CableDiagPL24,
    'DES-3200-18':CableDiagPL16,
    'DES-3200-28/C1':CableDiagPL24_C1,
    'DES-3200-18/C1':CableDiagPL16_C1,
    'DES-3028':CableDiagPL24,
},
    {
    'DES-3200-28':sysUpTime,
    'DES-3200-18':sysUpTime,
    'DES-3200-28/C1':sysUpTime,
    'DES-3200-18/C1':sysUpTime,
    'DES-3028':sysUpTime,
},
    {
    'DES-3200-28':FWVer,
    'DES-3200-18':FWVer,
    'DES-3200-28/C1':FWVer,
    'DES-3200-18/C1':FWVer,
    'DES-3028':FWVer,
}
]