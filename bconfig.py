#coding=UTF8

# SNMP write-community
snmp_wcomm    = "private"
# Timeout in microseconds
snmp_timeout  = 300000
# "Retries = 1" means that all will be sended 2 queries
snmp_retries  = 2
# List of 'snmpset' commands for which snmp retries value always will be zero
no_retries = ['SaveConf', 'UploadConf_3200_AB', 'UploadConf_3200_C', 'UploadConf_3028']

# Processes/Threads
max_processes          = 4
max_devices_in_process = 4000
max_threads            = 8
max_requests_in_thread = 12

# Params
logfile = "/var/log/briseis.log"
query_interval = 300
sleep_interval = 0.2
sleep_after_set_requests = 1
set_iter_delay = 1.25
datasend_right_border = 30
try_fix_query_errors = 1
try_fix_counters = True
walk_before_set = True

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
GraphiteCarbonList    = [
    [True, "graphite1.localhost", 2003, "sw.",        ['RX', 'TX', 'RX_crc', 'CT', 'CPU']],
    [True, "graphite2.localhost", 1907, "{$device}.", ['RX', 'TX', 'RX_crc', 'CT', 'CPU', 'CNS', 'DS', 'UP', 'FW']],
    ]

# OIDs
default_info = {
    'sys_descr'    : '.1.3.6.1.2.1.1.1.0',
    'sys_name'     : '.1.3.6.1.2.1.1.5.0',
    }

# The compliance descriptions of models to their names. The list is checked before the first match
# Key - the substring part of the string in sysDescr or sysName
# Value - the locally significant name of the model
models_by_desc = [
    {'DES-3200-28/C1' : 'DES-3200-28_C1'},
    {'DES-3200-28'    : 'DES-3200-28'},
    {'DES-3200-18/C1' : 'DES-3200-18_C1'},
    {'DES-3200-18'    : 'DES-3200-18'},
    {'DES-3200-10'    : 'DES-3200-10'},
    {'DES-3028G'      : 'DES-3028G'},
    {'DES-3028'       : 'DES-3028'},
    {'DES-3026'       : 'DES-3026'},
    {'DGS-3100-24TG'  : 'DGS-3100-24TG'},
    {'DGS-3120-24SC/B': 'DGS-3120-24SC_B'},
    {'DGS-3120-24SC'  : 'DGS-3120-24SC'},
    {'DGS-3000-28SC'  : 'DGS-3000-28SC'},
    {'DGS-3000-24TC'  : 'DGS-3000-24TC'},
    {'DGS-3000-26TC'  : 'DGS-3000-26TC'},
    {'DGS-3612G'      : 'DGS-3612G'},
    {'DGS-3627G'      : 'DGS-3627G'},
    {'DGS-3620-28SC'  : 'DGS-3620-28SC'},
    {'BigIron RX'     : 'BigIron-RX'},
    {'BigIron 8000'   : 'Foundry'},
    {'BigIron 4000'   : 'Foundry'},
    {'FastIron 800'   : 'Foundry'},
    {'FastIron 400'   : 'Foundry'},
    {'FastIron SX 800': 'SX-800'},
    {'NetIron 800'    : 'Foundry'},
    {'IronWare'       : 'Foundry'},
    {'TurboIron-X24'  : 'Foundry'},
    {'c2950-MGMT'     : 'WS-C2950G-48-EI'},
    {'cat3550-12G'    : 'WS-C3550-12G'},
    {'Cat3550-12G'    : 'WS-C3550-12G'},
    {'Core7k-17'      : 'WS-C3550-12G'},
    {'Kalach_cat3550' : 'WS-C3550-12G'},
    {'Bereslavka-Cat' : 'WS-C3550-12G'},
    {'CiscoWisi'      : 'WS-C3560X-24'},
    {'AdmRack-c3750'  : 'WS-C3750-24PS-S'},
    {'Cat3750-48_TV'  : 'WS-C3750-48TS-S'},
    {'ATS10-5A.2_RoS' : 'WS-C3750G-16TD'},
    {'SCE8000'        : 'SCE8000'},
    {'Redback'        : 'Redback'},
    {'MES2124'        : 'MES-2124'},
    {'MES3124F'       : 'MES-3124F'},
    {'APC Web/SNMP'   : 'APC-Smart-UPS'},
    {'QSW-8370'       : 'QSW-8370'},
    ]

# Sets of commands for 'snmpset' operation
PassSet  = {
      1 : [],
     48 : ['SaveConf'],
     72 : ['UploadConf_3028'],
     96 : ['UploadConf_3200_C'],
    144 : ['UploadConf_3200_AB'],
    }

# Sets of metrics for 'snmpget/snmpwalk' operation
PassWalk = {
    1 : ['RX', 'TX', 'RX_crc', 'CT', 'CPU', 'CNS', 'DS', 'UP', 'FW'],
    2 : ['RX', 'TX', 'RX_crc', 'CT', 'CPU', 'CNS', 'DS', 'UP',     ],
    }

oids_set = {
    'DES-3200-28' : {
	'SaveConf'           : 'CfgSave',
	'UploadConf_3200_AB' : 'CfgUpload',
    },
    'DES-3200-18' : {
	'SaveConf'           : 'CfgSave',
	'UploadConf_3200_AB' : 'CfgUpload',
    },
    'DES-3200-10' : {
	'SaveConf'           : 'CfgSave',
	'UploadConf_3200_AB' : 'CfgUpload',
    },
    'DES-3200-28_C1' : {
	'SaveConf'           : 'CfgSave',
	'UploadConf_3200_C'  : 'CfgUpload',
    },
    'DES-3200-18_C1' : {
	'SaveConf'           : 'CfgSave',
	'UploadConf_3200_C'  : 'CfgUpload',
    },
    'DES-3028':{
	'SaveConf'           : 'CfgSave',
	'UploadConf_3028'    : 'CfgUpload',
    }
}

oids_walk = [
    {
    'DES-3200-28'    : 'CNS',
    'DES-3200-18'    : 'CNS',
    'DES-3200-10'    : 'CNS',
    'DES-3200-28_C1' : 'CNS',
    'DES-3200-18_C1' : 'CNS',
    'DES-3028'       : 'CNS',
    'DGS-3000-24TC'  : 'CNS',
    'DGS-3000-26TC'  : 'CNS',
    },
    {
    'DES-3200-28'    : 'Errors',
    'DES-3200-18'    : 'Errors',
    'DES-3200-10'    : 'Errors',
    'DES-3200-28_C1' : 'Errors',
    'DES-3200-18_C1' : 'Errors',
    'DES-3028'       : 'Errors',
    'DGS-3000-24TC'  : 'Errors',
    'DGS-3000-26TC'  : 'Errors',
    },
    {
    'DES-3200-28'    : 'RxTx',
    'DES-3200-18'    : 'RxTx',
    'DES-3200-10'    : 'RxTx',
    'DES-3200-28_C1' : 'RxTx',
    'DES-3200-18_C1' : 'RxTx',
    'DES-3028'       : 'RxTx',
    'DGS-3000-24TC'  : 'RxTx',
    'DGS-3000-26TC'  : 'RxTx',
    },
    {
    'DES-3200-28'    : 'DuplexStatus',
    'DES-3200-18'    : 'DuplexStatus',
    'DES-3200-10'    : 'DuplexStatus',
    'DES-3200-28_C1' : 'DuplexStatus',
    'DES-3200-18_C1' : 'DuplexStatus',
    'DES-3028'       : 'DuplexStatus',
    'DGS-3000-24TC'  : 'DuplexStatus',
    'DGS-3000-26TC'  : 'DuplexStatus',
    },
    {
    'DES-3200-28'    : 'sysUpTime',
    'DES-3200-18'    : 'sysUpTime',
    'DES-3200-10'    : 'sysUpTime',
    'DES-3200-28_C1' : 'sysUpTime',
    'DES-3200-18_C1' : 'sysUpTime',
    'DES-3028'       : 'sysUpTime',
    'DGS-3000-24TC'  : 'sysUpTime',
    'DGS-3000-26TC'  : 'sysUpTime',
    },
    {
    'DES-3200-28'    : 'FWVer',
    'DES-3200-18'    : 'FWVer',
    'DES-3200-10'    : 'FWVer',
    'DES-3200-28_C1' : 'FWVer',
    'DES-3200-18_C1' : 'FWVer',
    'DES-3028'       : 'FWVer',
    'DGS-3000-24TC'  : 'FWVer',
    'DGS-3000-26TC'  : 'FWVer',
    },
    {
    'DES-3200-28_C1' : 'swTempCurr',
    'DGS-3000-24TC'  : 'swTempCurr',
    'DGS-3000-26TC'  : 'swTempCurr',
    },
    {
    'DES-3200-28'    : 'CPUutil',
    'DES-3200-18'    : 'CPUutil',
    'DES-3200-10'    : 'CPUutil',
    'DES-3200-28_C1' : 'CPUutil',
    'DES-3200-18_C1' : 'CPUutil',
    'DES-3028'       : 'CPUutil',
    'DGS-3000-24TC'  : 'CPUutil',
    'DGS-3000-26TC'  : 'CPUutil',
    },
]
