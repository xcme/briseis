#coding=UTF8

# SNMP write-community
snmp_wcomm    = "private"
# SNMP timeout in microseconds
snmp_timeout  = 300000
# SNMP additional retries. When sets in 1 means that will be send 2 queries at all
snmp_retries  = 1
# List of 'snmpset' commands for which snmp retries value always will be set to zero
no_retries = ['SaveConf', 'UploadConf_3200_AB', 'UploadConf_3200_C', 'UploadConf_3028']

# Processes and threads
max_processes          = 4
max_devices_in_process = 4000
max_threads            = 8
max_requests_in_thread = 12

# Logging
log_file = "/var/log/briseis.log"
log_size = 1048576
log_backupcount = 4

# Parameters
query_interval = 300
sleep_interval = 0.2
sleep_after_set_requests = 1
set_iter_delay = 1.25
datasend_right_border = 30
try_fix_query_errors = 1
try_fix_counters = True
walk_before_set = True
allow_empty_data = False

# MySQL settings. Cannot be used with PostgreSQL simultaneously
mysql_addr  = "mysql.localhost"
mysql_user  = "user"
mysql_pass  = "password"
mysql_base  = "devices"

# PostgreSQL settings. When 'use_postgresql' sets to True the MySQL will not be used
postgresql_addr = "postgresql.localhost"
postgresql_user = "user"
postgresql_pass = "password"
postgresql_base = "devices"
use_postgresql  = True

# Database query for neither MySQL or PostgreSQL
db_query = """SELECT deviceid AS id, ip, community AS wcomm FROM devices.devices;"""

# MySQL settings for statistic server
useMySQLstat = True
mysql_stat_addr = "localhost"
mysql_stat_user = "briseis"
mysql_stat_pass = "briseis_pass"
mysql_stat_base = "blackhole"
mysql_stat_cset = "utf8"
mysql_stat_tabl = "stats"

# Graphite settings
GraphiteCarbonList    = [
    [True,  "graphite1.localhost", 2003, "sw.",        ['RX', 'TX', 'RX_CRC', 'CPU', 'CT' ]],
    [False, "graphite2.localhost", 1907, "{$device}.", ['RX', 'TX', 'RX_CRC', 'CPU', 'CT', 'DS', 'CNS', 'UP', 'FW']],
    ]

# Sets of commands for 'snmpset' operation
PassSet  = {
      1 : [],
#     48 : ['SaveConf'],
#     72 : ['UploadConf_3028'],
#     96 : ['UploadConf_3200_C'],
#    144 : ['UploadConf_3200_AB'],
    }

# Command-to-'metric set' mapping
oids_set = {
    'DES-3200-28' : {
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3200_AB' : 'sms_CfgUpload',
    },
    'DES-3200-18' : {
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3200_AB' : 'sms_CfgUpload',
    },
    'DES-3200-10' : {
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3200_AB' : 'sms_CfgUpload',
    },
    'DES-3200-28_C1' : {
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3200_C'  : 'sms_CfgUpload',
    },
    'DES-3200-18_C1' : {
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3200_C'  : 'sms_CfgUpload',
    },
    'DES-3028':{
	'SaveConf'           : 'sms_CfgSave',
	'UploadConf_3028'    : 'sms_CfgUpload',
    }
}

# Sets of metrics for 'snmpget/snmpwalk' operation
PassWalk = {
    1 : ['RX', 'TX', 'RX_CRC', 'CT', 'CPU', 'CNS', 'DS', 'UP', 'FW'],
    2 : ['RX', 'TX', 'RX_CRC', 'CT', 'CPU', 'CNS', 'DS', 'UP',     ],
    }

# Model-to-'metric sets' mapping
oids_walk = {
'DGS-3000-26TC'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime', 'ms_Temp', 'ms_FWVer', 'ms_CNS' ],
'DGS-3000-24TC'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime', 'ms_Temp', 'ms_FWVer', 'ms_CNS' ],
'DES-3200-28_C1'     : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime', 'ms_Temp', 'ms_FWVer', 'ms_CNS' ],
'DES-3200-18_C1'     : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime', 'ms_Temp', 'ms_FWVer', 'ms_CNS' ],
'DES-3200-10_C1'     : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime', 'ms_Temp', 'ms_FWVer', 'ms_CNS' ],
'DES-3200-28'        : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime',            'ms_FWVer', 'ms_CNS' ],
'DES-3200-18'        : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime',            'ms_FWVer', 'ms_CNS' ],
'DES-3200-10'        : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime',            'ms_FWVer', 'ms_CNS' ],
'DES-3028'           : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS', 'ms_CPU', 'ms_UpTime',            'ms_FWVer', 'ms_CNS' ],
'DGS-1100-06_ME'     : [ 'ms_RxTx',              'ms_DS',           'ms_UpTime',                        'ms_CNS' ],
'SNR-S2940-8G'       : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-10
'DGS-3120-24SC'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-24
'DGS-3120-24SC_B'    : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-24
'MES-1024'           : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-24
'Alpha-A26'          : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-26
'Cat2950G-24'        : [ 'ms_RxTx',                                 'ms_UpTime',                                 ], # SymLink to SW-Common-26
'Cat2950T-24'        : [ 'ms_RxTx',                                 'ms_UpTime',                                 ], # SymLink to SW-Common-26
'SNR-S2950-24G'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-26
'DGS-3426G'          : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-26
'Alpha-A28F'         : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'Alpha-A28F_NOS'     : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'SNR-S2960-24G'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'SNR-S2965-24T'      : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'SNR-S2970G-24S'     : [ 'ms_RxTx',                                 'ms_UpTime',                                 ], # SymLink to SW-Common-28
'QSW-2800-28T'       : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'QSW-3470-28T'       : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'DES-3200-28F'       : [ 'ms_RxTx', 'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                                 ], # SymLink to SW-Common-28
'Cat2950G-48'        : [ 'ms_Rx', 'ms_Tx',                          'ms_UpTime',                                 ], # SymLink to SW-Common-50
'QSW-3470-52T'       : [ 'ms_Rx', 'ms_Tx',  'ms_RX_CRC', 'ms_DS',           'ms_UpTime',                         ], # SymLink to SW-Common-52
}

# The compliance descriptions of models to their names. The list is checked until first match
# Key - the substring part of the string in sysDescr or sysName
# Value - the locally significant name of the model
models_by_desc = [
    {'DES-3200-28/C1'  : 'DES-3200-28_C1'},
    {'DES-3200-28F'    : 'DES-3200-28F'},
    {'DES-3200-28'     : 'DES-3200-28'},
    {'DES-3200-26'     : 'DES-3200-26'},
    {'DES-3200-18/C1'  : 'DES-3200-18_C1'},
    {'DES-3200-18'     : 'DES-3200-18'},
    {'DES-3200-10/C1'  : 'DES-3200-10_C1'},
    {'DES-3200-10'     : 'DES-3200-10'},
    {'DES-3526'        : 'DES-3526'},
    {'DES-3028G'       : 'DES-3028G'},
    {'DES-3028'        : 'DES-3028'},
    {'DES-3026'        : 'DES-3026'},
    {'DES-1228/ME'     : 'DES-1228_ME'},
    {'DES-1228'        : 'DES-1228'},
    {'DGS-1210-28'     : 'DGS-1210-28'},
    {'DGS-1210-12TS/ME': 'DGS-1210-12TS_ME'},
    {'DES-1210-10'     : 'DES-1210-10'},
    {'DGS-3100-24TG'   : 'DGS-3100-24TG'},
    {'DGS-3120-24PC'   : 'DGS-3120-24PC'},
    {'DGS-3120-24SC/B' : 'DGS-3120-24SC_B'},
    {'DGS-3120-24SC'   : 'DGS-3120-24SC'},
    {'DGS-3000-28SC'   : 'DGS-3000-28SC'},
    {'DGS-3000-24TC'   : 'DGS-3000-24TC'},
    {'DGS-3000-26TC'   : 'DGS-3000-26TC'},
    {'DGS-3612G'       : 'DGS-3612G'},
    {'DGS-3627G'       : 'DGS-3627G'},
    {'DGS-3620-28SC'   : 'DGS-3620-28SC'},
    {'DGS-3420-26SC'   : 'DGS-3420-26SC'},
    {'DGS-3120-24PC'   : 'DGS-3120-24PC'},
    {'DGS-3426G'       : 'DGS-3426G'},
    {'DGS-3426'        : 'DGS-3426'},
    {'DES-2108'        : 'DES-2108'},
    {'DES-1226G'       : 'DES-1226G'},
    {'DGS-1100-06/ME'  : 'DGS-1100-06_ME'},
    {'Alpha-A28F'      : 'Alpha-A28F'},
    {'NOS'             : 'Alpha-A28F_NOS'},
    {'Alpha A26'       : 'Alpha-A26'},
    {'SNR-S2940-8G'    : 'SNR-S2940-8G'},
    {'SNR-S2950-24G'   : 'SNR-S2950-24G'},
    {'SNR-S2960-24G'   : 'SNR-S2960-24G'},
    {'SNR-S2960-48G'   : 'SNR-S2960-48G'},
    {'SNR-S2965-8T'    : 'SNR-S2965-8T'},
    {'SNR-S2965-24T'   : 'SNR-S2965-24T'},
    {'SNR-S2970G-24S'  : 'SNR-S2970G-24S'},
    {'SNR-S2980G-24F'  : 'SNR-S2980G-24F'},
    {'SNR-S2985G-24T'  : 'SNR-S2985G-24T'},
    {'SNR-S2985G-48T'  : 'SNR-S2985G-48T'},
    {'SNR-S2990G-24FX' : 'SNR-S2990G-24FX'},
    {'SNR-S2990G-24T'  : 'SNR-S2990G-24T'},
    {'SNR-S3750G-24S'  : 'SNR-S3750G-24S'},
    {'SNR-S3750G-48S'  : 'SNR-S3750G-48S'},
    {'QSW-3470-28T'    : 'QSW-3470-28T'},
    {'QSW-3470-52T'    : 'QSW-3470-52T'},
    {'QSW-2800-28T'    : 'QSW-2800-28T'},
    {'QTECH'           : 'QTECH'},
    {'MES-1024'        : 'MES-1024'},
    {'MES-2124'        : 'MES-2124'},
    {'WS-C2950G-24'    : 'Cat2950G-24'},
    {'WS-C2950G-48'    : 'Cat2950G-48'},
    {'WS-C2950T-24'    : 'Cat2950T-24'},
    {'C3750'           : 'Cat3750'},
    {'C3500XL'         : 'C3500XL'},
    {'BayStack 470'    : 'Nortel470'},
    {'Switch 470-24T'  : 'Nortel470'},
    {'Delta D48E'      : 'Delta D48E'},
    ]
