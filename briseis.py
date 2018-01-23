#!/usr/bin/env python2
#coding=UTF8
#started              (2014.08.10)
#released             (2015.03.05)
#current ver. 4.1.23  (2018.01.23)
# Формат 'version': <текущий год - год начала разработки>.<месяц последнего изменения>.<день последнего изменения>

import multiprocessing, threading, netsnmp, time, sys, socket, MySQLdb, logging, os, psycopg2
from logging.handlers import RotatingFileHandler
from    math import ceil
from  daemon import Daemon

from bconfig import snmp_wcomm, snmp_timeout, snmp_retries, no_retries
from bconfig import max_processes, max_devices_in_process, max_threads, max_requests_in_thread
from bconfig import log_file, log_size, log_backupcount
from bconfig import query_interval, sleep_interval, sleep_after_set_requests, set_iter_delay
from bconfig import datasend_right_border, try_fix_query_errors, try_fix_counters, walk_before_set, allow_empty_data
from bconfig import mysql_addr, mysql_user, mysql_pass, mysql_base
from bconfig import db_query
from bconfig import postgresql_addr, postgresql_user, postgresql_pass, postgresql_base, use_postgresql
from bconfig import useMySQLstat, mysql_stat_addr, mysql_stat_user, mysql_stat_pass, mysql_stat_base, mysql_stat_cset, mysql_stat_tabl
from bconfig import GraphiteCarbonList
from bconfig import PassSet, PassWalk, oids_set, oids_walk, models_by_desc

# Настройка системы логирования сообщения
log_handler = RotatingFileHandler(log_file, maxBytes = log_size, backupCount = log_backupcount)
log_formatter = logging.Formatter('%(asctime)s Briseis [%(process)d]: %(message)s')
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.addHandler(log_handler)
logger.setLevel(logging.DEBUG)

# Добавляем директорию 'devices' в список path. Это нужно, чтобы демон мог находить модули в этой директории
sys.path.append('%s%sdevices' % (sys.path[0], os.sep))

# Функция проверки корректности IP-адреса
def is_valid_ipv4_address(address):
    try:
	socket.inet_pton(socket.AF_INET, str(address))
    except AttributeError:  # no inet_pton here, sorry
	try:
	    socket.inet_aton(str(address))
	except socket.error:
	    return False
	return address.count('.') == 3
    except socket.error:  # not a valid address
	return False
    return True

# Функция для получения списка устройств из базы MySQL или PostgreSQL
def GetDataFromDB():
    xsql_data = ''
    # Пробуем подключиться к базе данных PostgreSQL либо MySQL. Используем таймаут в 2 секунды
    try:
	if use_postgresql == True:
	    db_conn = psycopg2.connect( host = postgresql_addr, user = postgresql_user, password = postgresql_pass, dbname = postgresql_base, connect_timeout = 2 )
	else:
	    db_conn = MySQLdb.connect( host = mysql_addr, user = mysql_user, passwd = mysql_pass, db = mysql_base, connect_timeout = 2 )
    # Если возникла ошибка при подключении, сообщаем об этом в лог и возвращаем пустой список
    except psycopg2.Error as p_err:
	logger.info("ERROR: PostgreSQL Error (%s): %s", postgresql_addr, p_err.args)
	return xsql_data
    except MySQLdb.Error as m_err:
	logger.info("ERROR: MySQL Error (%s): %s", mysql_addr, m_err.args[1])
	return xsql_data
    # Если ошибок не было, сообщаем в лог об успешном подключении и создаем 'курсор'
    else:
	if use_postgresql == True:
	    logger.info("INFO: Connection tor PostgreSQL Server '%s' established", postgresql_addr)
	else:
	    logger.info("INFO: Connection tor MySQL Server '%s' established", mysql_addr)
	db_cr = db_conn.cursor()

	# Пробуем выполнить запрос к базе и получить все данные из 'курсора'
	try:
	    db_cr.execute(db_query)
	    xsql_data = db_cr.fetchall()
	# Если возникла ошибка при выполнении запроса, сообщаем об этом в лог и возвращаем пустой список
	except psycopg2.Error as p_err:
	    logger.info("ERROR: PostgreSQL Query failed: %s", p_err.args)
	    return xsql_data
	except MySQLdb.Error as m_err:
            logger.info("ERROR: MySQL Query failed: %s", m_err.args[1])
	    return xsql_data
	# Если ошибок не возникло, сообщаем в лог об успешном подключении
	else:
	    if use_postgresql == True:
		logger.info("INFO: PostgreSQL Query OK. %s rows found.", len(xsql_data))
	    else:
		logger.info("INFO: MySQL Query OK. %s rows found.", len(xsql_data))
	# Закрываем подключение
	finally:
	    db_conn.close()
    # Возвращаем полученные данные
    return xsql_data

# Функция для получения для отправки статистики в базу MySQL
def SendDataToMySQL(mysql_stat_addr, mysql_stat_user, mysql_stat_pass, mysql_stat_base, mysql_stat_cset, mysql_stat_tabl, KeyList, devices, qtime):
    try:
	mysql_stat_conn = MySQLdb.connect(host=mysql_stat_addr, user=mysql_stat_user, passwd=mysql_stat_pass, db=mysql_stat_base, charset=mysql_stat_cset, connect_timeout=1)
	mysql_stat_conn.autocommit(True)
    except MySQLdb.Error as err:
	logger.info("ERROR: Can't connect to MySQL statistics server '%s': %s", mysql_stat_addr, err.args[1])
    else:
	logger.info("INFO: Connection to MySQL statistics Server '%s' established", mysql_stat_addr)
	# Создаем 'курсор'. (Особая MySQLdb-шная магия)
	mysql_stat_cr  = mysql_stat_conn.cursor()
    finally:
	send_query={'query':'','count':0,'total':0}

    try:
	mysql_stat_cr.execute("TRUNCATE `stats`;")
    except:
	pass

    for dev_id in KeyList:
	# Собираем запросы в очередь. Если счетчик очереди пуст, начинаем запись с SQL-команд, иначе просто добавляем данные
	if send_query['count'] == 0:
	    send_query['query']  = "INSERT INTO {0}.{1} ({1}.device_id,{1}.host,{1}.mname,{1}.set_timestamp,{1}.walk_timestamp,{1}.queries,{1}.avail,{1}.metrics,{1}.errors,{1}.time) VALUES ".format(mysql_stat_base,mysql_stat_tabl)
	send_query['query'] += "({0},'{1}',SUBSTR('{2}',1,16),{3},{4},{5},{6},{7},{8},{9}),".format(
	    dev_id,
	    devices[dev_id]['ip'],
	    devices[dev_id]['mname'],
	    devices[dev_id]['set_timestamp'],
	    devices[dev_id]['walk_timestamp'],
	    devices[dev_id]['queries'],
	    devices[dev_id]['avail'],
	    devices[dev_id]['metrics'],
	    devices[dev_id]['errors'],
	    devices[dev_id]['time']
	    )
	send_query['count'] += 1
	# Если в очереди накопилось 10 или более запросов или достигнут конец списка, пробуем отправить данные в базу
	if (send_query['count'] >= 10) or (dev_id==KeyList[-1]):
	    try:
		mysql_stat_cr.execute(send_query['query'][:-1])
	    except:
		pass
	    else:
		send_query['total'] += send_query['count']
	    send_query['count'] = 0
	    send_query['query'] = ''
    try:
	mysql_stat_conn.close()
    except:
	pass
    logger.info("INFO: Sended {} entries to statictics server. Elapsed time {:.4f} sec".format(send_query['total'],time.time()-qtime))

# Функция для подготовки словаря устройств
def Prepare_Devices(dev_tmp):
    dev = {}
    # Создаем ключи словаря:
    for line in dev_tmp:
	dev[line[0]]={}
    for line in dev_tmp:
	# Словарь будет иметь вид { id : { 'ip' : value, 'wcomm' : value, ... } }
	dev[line[0]].update({'ip':line[1], 'wcomm':line[2], 'set_timestamp':0, 'walk_timestamp':0, 'queries':0, 'avail':0, 'metrics':0, 'errors':0, 'time':0, 'data':{}, 'set_res':{}})
    return dev

def GetDevicesIDLists(keylist,itr,iter_cnt,max_threads,max_requests_in_thread):
    # Узнаем сколько осталось сделать запросов на текущий момент
    queries_left = len(keylist)-(itr-1)*max_threads*max_requests_in_thread
    # Оптимальное число потоков (остаток или максимум, если осталось еще много)
    need_threads = min(queries_left,max_threads)
    # Оптимальное число запросов в потоке равно макимальному, кроме последнеей итерации (+4)
    if itr<iter_cnt:
	optimal_requests_in_thread = max_requests_in_thread
	remaining_queries=0
    else:
	optimal_requests_in_thread = int( round( float(queries_left) / need_threads ) )
	remaining_queries = queries_left - need_threads * optimal_requests_in_thread
	# Переменная remaining_queries содержит число запросов, которые не поместились в потоки. Например, требуется 6 запросов,
	# но имеется только 4 потока. В каждом потоке будет по 1 запросу и еще 2 попадут в эту переменную
	# При группировке индексов устройств эта переменная будет учтена. В итоге получится 2+2+1+1 (6) запросов
    shiftpos = (itr - 1) * max_threads * max_requests_in_thread # Начальная позиция выборки в основном списке устройств
    slice_indexes = keylist[shiftpos:shiftpos + need_threads * optimal_requests_in_thread + remaining_queries] # Выборка номеров индексов основного списка устройств
    # Окончательный список списков (slice_dev_id), где номера индексов группирутся согласно определенному числу потоков и запросов в потоке
    # Будет выглядеть так: [[78L, 335L, 464L], [466L, 341L, 463L], [92L, 481L, 422L], [492L, 370L, 116L]]
    # Здесь число потоков (need_threads)=4, а число запросов в потоке (optimal_requests_in_thread)=3
    slice_dev_id = []
    # Начальная позиция выборки в списке индексов
    id_pos = 0
    for i in range(need_threads):
	# Длина выборки. Если есть лишние запросы, длина увеличится на единичку
	shft = optimal_requests_in_thread + int(remaining_queries>0)
	# В список добавляется новая группа идентификаторов
	slice_dev_id.append(slice_indexes[id_pos:id_pos+shft])
	# Определяется позиция для следующей итерации
	id_pos+=shft
	# Значение декрементируется и может стать меньше нуля. Это допустимо, т.к. играют роль только положительные значения
	remaining_queries-=1
    return slice_dev_id, need_threads

class prcGetDeviceName(multiprocessing.Process):
    def __init__(self,devices,ids4prc,prcname,passnum):
	multiprocessing.Process.__init__(self)
	self.devices = devices
	self.ids4prc = ids4prc
	self.prcname = prcname
	self.passnum = passnum
    def run(self):
	class thrGetDeviceName(threading.Thread):
	    def __init__(self,devices,ids4thr,passnum):
		threading.Thread.__init__(self)
		self.devices = devices
		self.ids4thr = ids4thr
		self.passnum = passnum
	    def run(self):
		for id_ in self.ids4thr:
		    devline = self.devices[id_]
		    # Получаем IP-адрес и проверяем его на корректность
		    ip = devline['ip']
		    if not is_valid_ipv4_address(ip):
			ip = '0.0.0.0'
		    # Получаем SNMP-Community для устройства
		    snmp_comm_this_device = snmp_wcomm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm'] != '':
			snmp_comm_this_device = devline['wcomm']
		    # Параметры и соответствующие им OID, необходимые для определения модели устройства
		    identify_oids = { 'sys_descr' : '.1.3.6.1.2.1.1.1.0', 'sys_contact' : '.1.3.6.1.2.1.1.4.0', 'sys_name' : '.1.3.6.1.2.1.1.5.0' }
		    # Формируем структуру varlist/varbind из параметров, перечисленных в identify_oids
		    snmp_var   = netsnmp.VarList(*map(netsnmp.Varbind, sorted(identify_oids.values())))
		    # Фиксируем текущее время
		    start_time = time.time()
		    # Выполняем опрос устройства
		    snmp_query = netsnmp.snmpget(*snmp_var, Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_timeout, Retries = snmp_retries, UseNumeric = 1)
		    # Время, затраченное на опрос
		    query_time = int((time.time()-start_time)*1000)
		    # Из полученных данных формируем словарь, где ключом является OID из identify_oids, а значением - полученное в ходе опроса значение:
		    # { '.1.3.6.1.2.1.1.1.0' : $sys_descr, '.1.3.6.1.2.1.1.4.0' : $sys_contact, '.1.3.6.1.2.1.1.5.0' : $sys_name }
		    sys_oids = dict([ [ '.'.join([var.tag, var.iid]), var.val ] for var in snmp_var ])
		    # Формируем словарь dev_info, комбинируя identify_oids и sys_oids. Если устройство недоступно, то все три значения будут None
		    dev_info = {'sys_descr': None, 'sys_contact': None, 'sys_name': None}
		    try:
			for sys_id in identify_oids:
			    dev_info[sys_id] = sys_oids[identify_oids[sys_id]]
		    except:
			pass
		    # Проверяем, есть ли None в значениях dev_info. Если 'нет', значит какой то ответ был получен и модель пока считается 'Unknown'
		    if not (None in dev_info.values()):
			mname = 'Unknown'
			# Определяем модель по вхождению подстроки в значения sysDescr, sysContact и sysName. Проверка идет до первого соответствия
			for desc_model in models_by_desc:
			    if desc_model.keys()[0] in dev_info['sys_descr']:
				mname = desc_model.values()[0]
			    if desc_model.keys()[0] in dev_info['sys_contact']:
				mname = desc_model.values()[0]
			    if desc_model.keys()[0] in dev_info['sys_name']:
				mname = desc_model.values()[0]
			    if mname != 'Unknown':
				break
		    # Если ответ не был получен, то все значения dev_info будут None. Модель также будет None
		    else:
			mname = 'None'
		    devline['mname'] = mname
		    # Инкрементируем счетчик доступности, если ответ был получен
		    if mname != 'None':
			devline['avail'] += 1
		    # Считаем общее кол-во опросов устройства
		    devline['queries'] += 1
		    devline['time'] += query_time
		    self.devices[id_] = devline

#	logger.info("INFO: Process %s started. Processing %s entries...", self.prcname, len(self.ids4prc))
	# Узнаем необходимое количество опросов
	iter_cnt  = int(ceil(float(len(self.ids4prc))/max_threads/max_requests_in_thread))
	# Формируем список от 1 до N, чтобы было удобнее перебирать
	iter_list = map(lambda x: x+1,range(iter_cnt))
	for itr in iter_list:
	    slice_dev_id, need_threads = GetDevicesIDLists(self.ids4prc,itr,iter_cnt,max_threads,max_requests_in_thread)
	    # Список потоков
	    my_thrs_G = []
	    for t in range(need_threads):
		# Создание нового класса потоков
		thrGetD = thrGetDeviceName(self.devices,slice_dev_id[t],self.passnum)
		# Имена потоков имеют вид prcname.thr1, prcname.thr2,. .., prcname.thrN
		thrGetD.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_G.append(thrGetD)
		thrGetD.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_G:
		thr.join()
#	logger.info("INFO: Process %s finished", self.prcname)

class prcSetOIDs(multiprocessing.Process):
    def __init__(self,devices,ids4prc,prcname,WorkMetricsListS):
	multiprocessing.Process.__init__(self)
	self.devices = devices
	self.ids4prc = ids4prc
	self.prcname = prcname
	self.WorkMetricsListS = WorkMetricsListS
    def run(self):
	class thrSetOIDs(threading.Thread):
	    def __init__(self,devices,ids4thr,WorkMetricsListS):
		threading.Thread.__init__(self)
		self.devices = devices
		self.ids4thr = ids4thr
		self.WorkMetricsListS = WorkMetricsListS
	    def run(self):
		for id_ in self.ids4thr:
		    devline = self.devices[id_]
		    # Получаем IP-адрес и проверяем его на корректность
		    ip = devline['ip']
		    if not is_valid_ipv4_address(ip):
			ip = '0.0.0.0'
		    # Получаем SNMP-Community для устройства
		    snmp_comm_this_device = snmp_wcomm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm'] != '': snmp_comm_this_device = devline['wcomm']
		    device_model = devline['mname']
		    if device_model in oids_set:
			query = 'skipped'
			for paramname in sorted(oids_set[device_model].keys()):
			    start_time = time.time()
			    if paramname in self.WorkMetricsListS:
				current_snmp_retries = snmp_retries
				if paramname in no_retries:
				    current_snmp_retries = 0
				varlist = netsnmp.VarList(*[netsnmp.Varbind(*VarBindItem) for VarBindItem in oids_set[device_model][paramname]])
				query   = netsnmp.snmpset(*varlist, Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_timeout, Retries = current_snmp_retries, UseNumeric = 1)
				time.sleep(set_iter_delay)
			    # Время, затраченное на опрос
			    query_time = int((time.time()-start_time)*1000)
			    devline['time'] += query_time
			    devline['set_res'][paramname] = query
		    devline['set_timestamp'] = int(time.time())
		    self.devices[id_] = devline

#	logger.info("INFO: Process %s started. Processing %s entries...", self.prcname, len(self.ids4prc))
	# Узнаем необходимое количество опросов
	iter_cnt  = int(ceil(float(len(self.ids4prc))/max_threads/max_requests_in_thread))
	# Формируем список от 1 до N, чтобы было удобнее перебирать
	iter_list = map(lambda x: x+1,range(iter_cnt))
	# Получаем список ключей из devdict, отсортированный по времени
	for itr in iter_list:
	    slice_dev_id, need_threads = GetDevicesIDLists(self.ids4prc,itr,iter_cnt,max_threads,max_requests_in_thread)
	    # Список потоков
	    my_thrs_S = []
	    for t in range(need_threads):
		# Создание нового класса потоков
		thrSet = thrSetOIDs(self.devices,slice_dev_id[t],self.WorkMetricsListS)
		# Имена потоков имеют вид prcname.thr1, prcname.thr2,. .., prcname.thrN
		thrSet.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_S.append(thrSet)
		thrSet.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_S:
		thr.join()
#	logger.info("INFO: Process %s finished", self.prcname)


class prcWalkOIDs(multiprocessing.Process):
    def __init__(self,devices,ids4prc,prcname,WorkMetricsListW):
	multiprocessing.Process.__init__(self)
	self.devices = devices
	self.ids4prc = ids4prc
	self.prcname = prcname
	self.WorkMetricsListW = WorkMetricsListW
    def run(self):
	class thrWalkOIDs(threading.Thread):
	    def __init__(self,devices,ids4thr,WorkMetricsListW):
		threading.Thread.__init__(self)
		self.devices = devices
		self.ids4thr = ids4thr
		self.WorkMetricsListW = WorkMetricsListW
	    def run(self):
		for id_ in self.ids4thr:
		    devline = self.devices[id_]
		    # Получаем IP-адрес и проверяем его на корректность
		    ip = devline['ip']
		    if not is_valid_ipv4_address(ip):
			ip = '0.0.0.0'
		    # Получаем SNMP-Community для устройства
		    snmp_comm_this_device = snmp_wcomm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm'] != '': snmp_comm_this_device = devline['wcomm']
		    device_model = devline['mname']
		    if device_model in oids_walk:
			for metric_set_unpacked in oids_walk[device_model]:
			    start_time = time.time()
			    # Объявляем переменную, т.к. если встретится неизвестная модель, то она не будет определена
			    varlist = []
			    Get_notWalk = False
			    start_snmpwalk = False
			    # Перебираем имена параметров (метрик) в конкретно наборе данных. При этом решаем несколько задач
			    # 1. Определяем, будем использовать режим Get или же режим Walk
			    # 2. Получаем имя параметра для сравнения со списком набора метрик для опроса. Из '~RX' получим 'RX', из 'CNS..7' получим 'CNS'
			    # 3. Проверяем, находится ли полученный параметр в списке метрик, которые нужно опрашивать
			    for paramname in sorted(metric_set_unpacked.keys()):
				tmp_param = paramname
				if '.' in tmp_param:
				    Get_notWalk = True
				    tmp_param = tmp_param[0:tmp_param.find('.')]
				if '~' in tmp_param:
				    tmp_param = tmp_param.replace('~','')
				if (tmp_param in self.WorkMetricsListW):
				    start_snmpwalk = True
			    # Номер попытки опроса
			    q_try_num = 0
			    # Отсутствие ошибок опроса. 1 - ошибок нет, 0 - есть. Начальное значение должно быть 0, чтобы выполнился цикл опроса
			    q_noerr = 0
			    # Если проверка выше показала, что полученные метрики следует опросить, то выполняем опрос
			    if start_snmpwalk:
				# Выполняем опрос пока не исчерпаны попытки и не зафиксировано отсутствие ошибок
				while (q_try_num <= try_fix_query_errors and q_noerr != 1):
				    varlist = netsnmp.VarList(*map(netsnmp.Varbind, sorted(metric_set_unpacked.values())))
				    if Get_notWalk:
					query   = netsnmp.snmpget(*varlist,Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_timeout, Retries = snmp_retries, UseNumeric = 1)
				    else:
					query   = netsnmp.snmpwalk(varlist,Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_timeout, Retries = snmp_retries, UseNumeric = 1)
				    q_noerr = int(None not in [ v_item.tag for v_item in varlist ])
				    q_try_num += 1
			    # Время, затраченное на опрос
			    query_time = int((time.time()-start_time)*1000)
			    devline['time'] += query_time
			    # Перебираем полученные значения
			    for var_ in varlist:
				# Иногда ответ может быть не распознан. В таких случаях фиксируем ошибку
				# Параметр 'allow_empty_data' позволяет указать допустимо ли использование данных вида "пустая строка"
				# Модуль netsnmp не может отличить результат опроса, вернувшего пустую строку, от результата, не вернувшего ничего (например, при некорректном OID)
				# Изначально программа предназначалась для сбора числовых метрик, поэтому рекомендованное значение параметра 'allow_empty_data' - False
				if ( (var_.tag is not None) & (var_.iid is not None) & ((var_.val != '') or allow_empty_data) ):
				    full_oid = var_.tag + '.' + var_.iid
				else:
				    full_oid = ''
				    devline['errors'] += 1
				if ( (device_model in oids_walk) & (full_oid != '') ):
				    # Здесь k - имя параметра, по которому получим значение, а prep_k - имя ключа в 'data'
				    # В случае walk-запроса значения k и prep_k равны, а в случае get имя prep_k обрезается до первой точки, не включая ее
				    for k in metric_set_unpacked:
					# Если используем метод get, то получаем имя ключа из параметра k с начала до первой точки, не включая ее, и задаем трейлер
					# Для метода опроса walk имя ключа будет равно параметру k, а трейлер должен быть пустым
					if Get_notWalk:
					    prep_k = k[0:k.find('.')]
					    trailer = '*'
					else:
					    prep_k = k
					    trailer = '.'
					# Значение trailer прибавляем для избежания ложного срабатывания при сравнении OID, например ...1.2.3.2 и ....1.2.3.20
					# При Get-запросе full_oid всегда является "конечным", поскольку это "прицельный" запрос. Поэтому здесь используем "жесткий" трейлер = '*'
					# Теперь будут сравниваться .1.2.3.2* и .1.2.3.20*. Первое значение уже не входит во второе, как было бы в предыдущем случае
					# При Walk-запросе full_oid заранее неизвестен, поэтому используем "мягкий" трейлер = '.' (символ точки является частью OID)
					# Также при Walk-запросе у нас есть отдельное требование - ветки должны быть одной длины
					# Если оно выполнено, значит сравниваемые ветки разные и точку использовать допустимо. Ниже пример tmp_oid, которые "пересеклись" бы без трейлера
					# full_oid: .1.3.6.1.2.1.31.1.1.1.18.1, tmp_oid: .1.3.6.1.2.1.31.1.1.1.18 (вместе с трейлером '.' входит в full_oid)
					# full_oid: .1.3.6.1.2.1.31.1.1.1.1.1,  tmp_oid: .1.3.6.1.2.1.31.1.1.1.1  (вместе с трейлером '.' входит в full_oid)

					# Проверяем, есть ли значение параметра в полном OID
					if (metric_set_unpacked[k]+trailer in full_oid+trailer):
					    # Если условие выше выполнилось, значит распознана ожидаемая метрика, поэтому инкрементируем счетчик метрик
					    devline['metrics'] += 1
					    # Получаем оставшуюся часть от OID
					    remainder = full_oid.replace(metric_set_unpacked[k]+'.','')
					    # Если используем метод get, оставшаяся часть будет равна iid
					    if Get_notWalk:
						remainder = var_.iid
						# Альтернативный вариант для использования нескольких последних чисел OID в имени подраздела, например '7.100'
						if k.count('.')>1:
						    remainder = ".".join(full_oid.split(".")[-k.count('.'):])
					    # Например в конфиге указан OID 1.2.3.2.1, tag будет 1.2.3.2.1.X, iid - Y (может быть пустым). Полный OID (full_oid) будет 1.2.3.2.1.X.Y
					    # Имя раздела (словаря) будет k, а подраздела (ключа метрики) - remainder
					    if (prep_k not in devline['data']):
						devline['data'][prep_k]={}

					    # Если работаем со счетчиком:
					    if (prep_k[0:1] == '~'):
						# Пробуем получить предыдущее значение счетчика (prev_val) через try (так быстрее)
						# При неудаче считаем значение равным 0
						try:
						    prev_val = devline['data'][prep_k][remainder]
						    skipped = False
						except:
						    prev_val = 0
						    skipped = True

						# Пробуем получить новое значение счетчика (new_val) аналогичным способом
						# При неудаче также считаем значение равным 0
						try:
						    new_val = int(var_.val)
						except:
						    new_val = 0

						# Получаем имя ключа и разрядность счетчиков. ~ - 64-битные счетчики, ~~ - 32-битные
						# max_diff - максимальное значение трафика за query_interval на 100M и 10G интерфейсах соответственно
						if (prep_k[0:2] == '~~'):
						    new_k = prep_k[2:]
						    pw_ = 32
						    max_diff = query_interval*1000*1000*100/8
						else:
						    new_k = prep_k[1:]
						    pw_ = 64
						    max_diff = query_interval*1000*1000*1000*10/8
						if new_k not in devline['data']:
						    devline['data'][new_k] = {}

						# Записываем текущее значение счетчика
						devline['data'][prep_k][remainder] = new_val

						# Если удалось получить предыдущее значение, то пробуем вычислить разницу.
						if not skipped:
						    # Если это не получится (prev_val - не число), то просто используем значение new_val
						    try:
							new_diff = new_val - prev_val
						    except:
							pass

						    # Если разница получилась отрицательной, компенсируем переполнение счетчика
						    if new_diff < 0:
							new_diff = new_diff + (pow(2,pw_)-1)

						    # Если разница превысила максимально возможную, считаем, что счетчик был сброшен между опросами
						    # В этом случае обнуляем разницу, т.к. на графике лучше иметь спад до 0, чем пик, уходящий в бесконечность
						    if try_fix_counters:
							if new_diff > max_diff:
							    new_diff = 0

						    # Записываем разницу между новым и старым значениями счетчика
						    devline['data'][new_k][remainder] = new_diff
					    # Если это не счетчик, а обычная метрика:
					    else:
						devline['data'][prep_k][remainder] = var_.val
				# Итак, еще раз: full_oid - полный OID, metric_set_unpacked[k] - OID в конфиге, k - имя параметра для OID в конфиге, например 'RX_crc.1'
				# prep_k - имя ключа в 'data', которое при walk равно k, а при get обрезается до точки, т.к. точка в имени указывает на использование get
				# new_k - новое имя ключа, получаемое из prep_k, где обрезаются начальные символы ~, указывающие на тип 'счетчик'
				# remainder - имя ключа метрики
		    devline['walk_timestamp'] = int(time.time())
		    self.devices[id_] = devline

#	logger.info("INFO: Process %s started. Processing %s entries...", self.prcname, len(self.ids4prc))
	# Узнаем необходимое количество опросов
	iter_cnt  = int(ceil(float(len(self.ids4prc))/max_threads/max_requests_in_thread))
	# Формируем список от 1 до N, чтобы было удобнее перебирать
	iter_list = map(lambda x: x+1,range(iter_cnt))
	for itr in iter_list:
	    slice_dev_id, need_threads = GetDevicesIDLists(self.ids4prc,itr,iter_cnt,max_threads,max_requests_in_thread)
	    # Список потоков
	    my_thrs_W = []
	    for t in range(need_threads):
		# Создание нового класса потоков
		thrWalk = thrWalkOIDs(self.devices,slice_dev_id[t],self.WorkMetricsListW)
		# Имена потоков имеют вид prcname.thr1, prcname.thr2,. .., prcname.thrN
		thrWalk.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_W.append(thrWalk)
		thrWalk.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_W:
		thr.join()
#	logger.info("INFO: Process %s finished", self.prcname)

def SendDataToCarbon(CarbonData, CarbonAddress, CarbonPort):
    stime = time.time()
    try:
	sock = socket.create_connection((CarbonAddress, CarbonPort), timeout = 3)
	sock.settimeout(None)
    except socket.error as s_err:
	logger.info("ERROR: Can't connect to Graphite/Carbon (%s:%s): %s", CarbonAddress, CarbonPort, s_err)
    else:
	logger.info("INFO: Connection to Graphite/Carbon (%s:%s) established", CarbonAddress, CarbonPort)
	try:
	    for metric in CarbonData:
		sock.sendall(metric+"\n")
	    sock.close()
	except:
	    logger.info("ERROR: Can't send data to Graphite/Carbon. Something wrong!")
	else:
	    logger.info("INFO: {} metrics has been sent to Graphite/Carbon ({}:{}) for {:.4f} sec".format(len(CarbonData), CarbonAddress, CarbonPort, time.time()-stime))


def main():
    logger.info("INFO: Daemon 'Briseis' started...")

    # Получаем список модулей из директории 'devices'. Модули - это файлы, имена которых заканчиваютя на 'py'
    modules = [fname for fname in next(os.walk('%s%sdevices' % (sys.path[0], os.sep)))[2] if fname.endswith('py')]
    # Перебираем список модулей. У каждого убираем расширение 'py' и пробуем подключить его как модуль Python. При неудаче пишем в лог.
    for module in modules:
	module_name = os.path.splitext(module)[0]
	try:
	    module_data = __import__(module_name)
	except:
	    logger.info("CRITICAL: Can't import module '%s'! Exiting...", module)
	    sys.exit(2)
	else:
	    # Если модуль подключен успешно, перебираем весь набор oids_walk и пытаемся подставить в него объекты из модуля
	    for device_model in oids_walk:
		if device_model == module_name:
		    for metric_set_num, metric_set in enumerate(oids_walk[device_model]):
			if metric_set in dir(module_data):
			    try:
				oids_walk[device_model][metric_set_num] = getattr(module_data, metric_set)
			    except:
				pass

	    # То же самое делаем и для набора oids_set
	    for device_model in oids_set:
		if device_model == module_name:
		    for query_name in sorted(oids_set[device_model].keys()):
			if oids_set[device_model][query_name] in dir(module_data):
			    try:
				oids_set[device_model][query_name] = getattr(module_data, oids_set[device_model][query_name])
			    except:
				pass

    # Снова перебираем набор oids_walk и те объекты, которые не были найдены в модулях (а значит отсутствуют), заменяем на пустые
    for device_model in oids_walk:
	for metric_set_num, metric_set in enumerate(oids_walk[device_model]):
	    if isinstance(metric_set, str):
		oids_walk[device_model][metric_set_num] = {}
		logger.info("WARNING: Metric set '%s' has not been determined for device '%s'!", metric_set, device_model)

    # Аналогичную процедуру делаем и для набора oids_set
    for device_model in oids_set:
	for query_name in sorted(oids_set[device_model].keys()):
	    if isinstance(oids_set[device_model][query_name], str):
		oids_set[device_model][query_name] = []
    # Итоговая структура oids_walk должна быть примерно такой:
    #{
    #'device_model1':[ {'metric_name1':'metric_oid1','metric_name2':'metric_oid2',}, {'metric_name3':'metric_oid3','metric_name4':'metric_oid4',} ]
    #'device_model2':[ {'metric_name1':'metric_oid1','metric_name2':'metric_oid2',}, {'metric_name3':'metric_oid3','metric_name4':'metric_oid4',} ]
    #}
    # А вот итоговая структура oids_set:
    #{
    #'device_model1':{'query_name1':[ [tag1,iid1,val1,type1],[tag2,iid2,val2,type2],...,[tagN,iidN,valN,typeN] ],
    #                 'query_name1':[ [tag1,iid1,val1,type1],[tag2,iid2,val2,type2],...,[tagN,iidN,valN,typeN] ],},
    #'device_model2':{...}
    #}

    passnum = 1
    devices = {}
    timer = int(time.time())
    while True:
	if ((int(time.time()) - timer >= query_interval) or (passnum == 1)):
	    logger.info("INFO: -------       Pass №{} processing...        -------".format(passnum))
	    timer = int(time.time())
	    # Получаем IP и ID устройств из базы данных
	    devices_tmp = GetDataFromDB()
	    # Преобразовываем результат запроса в словарь
	    devices_tmp = Prepare_Devices(devices_tmp)
	    # Список ID устройств, которые отсутствуют в новой выборке
	    removed_devices = list(set(devices.keys())-set(devices_tmp.keys()))
	    # Список ID устройств, которые добавились в новой выборке
	    added_devices   = list(set(devices_tmp.keys())-set(devices.keys()))
	    # Пишем в лог об удаленных устройствах
	    for dev in removed_devices:
		logger.info("WARNING: (-) Device %s:%s was removed from database", dev, devices[dev]['ip'])
	    # При первом запуске пишем в лог общее количество добавленных устройств, а в остальных случаях перечисляем все добавленные
	    if passnum > 1:
		for dev in added_devices:
		    logger.info("WARNING: (+) Device %s:%s was added to database", dev, devices_tmp[dev]['ip'])
	    else:
		logger.info("WARNING: (+++) Added %s devices to database", len(devices_tmp))
	    # В новый словарь добавляем данные о доступности и времени опроса из старого
	    for dev in devices_tmp:
		# Делаем это в случае, если устройство отсутствует в списке добавленных, т.е. работа с ним уже велась
		if dev not in added_devices:
		    devices_tmp[dev]['avail']   = devices[dev]['avail']
		    devices_tmp[dev]['queries'] = devices[dev]['queries']
		    devices_tmp[dev]['time']    = devices[dev]['time']
		    devices_tmp[dev]['data']    = {}
		    if 'mname' in devices[dev]:
			device_model = devices[dev]['mname']
			if device_model in oids_walk:
			    for metric_set_unpacked in oids_walk[device_model]:
				for k in metric_set_unpacked:
				    prep_k = k
				    if '.' in k:
					prep_k = prep_k[0:prep_k.find('.')]
				    if ((k[0:1] == '~') & (prep_k in devices[dev]['data'])):
					devices_tmp[dev]['data'][prep_k] = devices[dev]['data'][prep_k]

	    devices = multiprocessing.Manager().dict(devices_tmp.copy())
	    devices_tmp.clear()

	    for attempt in range(2):
		#При первом проходе обрабатываем все устройства
		if attempt == 0: devdict = devices
		# При втором - только те, что не были доступными в первый раз
		if attempt == 1: devdict = skipped_devices
		# Узнаем необходимое количество опросов (для процессов)
		prc_iter_cnt  = int(ceil(float(len(devdict))/max_processes/max_devices_in_process))
		# Формируем список от 1 до N, чтобы было удобнее перебирать
		prc_iter_list = map(lambda x: x+1,range(prc_iter_cnt))
		# Получаем список ключей из devdict, отсортированный по времени
		KeyList=sorted(devdict.keys(),key=lambda k: devices[k]['time'])
		qtime = time.time()
		for prc_itr in prc_iter_list:
		    slice_dev_id, need_processes = GetDevicesIDLists(KeyList, prc_itr, prc_iter_cnt, max_processes, max_devices_in_process)
		    # Список процессов
		    my_prcs_G = []
		    for t in range(need_processes):
			# Создание нового класса процессов
			prcGetD = prcGetDeviceName(devices,slice_dev_id[t],"prcG{}".format(t+1),passnum)
			# Процесс добавляется в список процессов. Здесь это нужно, чтобы потом корректно отследить завершение процессов через join
			my_prcs_G.append(prcGetD)
			prcGetD.start()

		    # Перебираем список процессов и ждем, пока все будут завершены
		    for prc in my_prcs_G:
			prc.join()
		logger.info("INFO: Polling devices from the database. Attempt #{} of 2 completed for {:.4f} sec".format(attempt+1,time.time()-qtime))
		skipped_dev_cnt = 0
		skipped_devices = {}
		for d in devices.copy():
		    if devices[d]['mname'] == 'None':
			skipped_dev_cnt += 1
			skipped_devices[d] = devices[d]
		if skipped_dev_cnt > 0:
		    logger.info("WARNING: Found %s offline devices for #%s iteration!", skipped_dev_cnt, attempt + 1)
		# Проверяем, есть ли нераспознанные устройства
		unknown_dev_cnt = [ devices[d]['mname'] for d in devices.copy() ].count('Unknown')
		if unknown_dev_cnt > 0:
		    logger.info("WARNING: Found %s unknown devices for #%s iteration!", unknown_dev_cnt, attempt + 1)

	    devices_tmp = devices.copy()
	    for dev in devices.copy():
		if devices[dev]['mname']=='None':
		    del devices_tmp[dev]
	    devdict = devices_tmp
	    # Узнаем необходимое количество опросов (для процессов)
	    prc_iter_cnt  = int(ceil(float(len(devdict))/max_processes/max_devices_in_process))
	    # Формируем список от 1 до N, чтобы было удобнее перебирать
	    prc_iter_list = map(lambda x: x+1,range(prc_iter_cnt))

	    # Выполняем walk и set операции. Их порядок определяется флагом walk_before_set.
	    # В предыдущих версиях последовательность была задана жестко. Сильно менять логику не хотелось и потому было решено добавить такой workaround ;)
	    for walk_or_set_pass in range(1,3):
		# Получаем список ключей из devdict, отсортированный по времени
		KeyList   = sorted(devdict.keys(),key=lambda k: devices[k]['time'])
		qtime = time.time()
		if (walk_before_set and walk_or_set_pass == 1) or (not walk_before_set and walk_or_set_pass == 2):
		    # Получаем список метрик на основе номера прохода, который кратен максимальному ключу из набора метрик
		    WorkMetricsListW = PassWalk[max([walkkey for walkkey in PassWalk if passnum % walkkey == 0])]
		    logger.info("INFO: Sending get/walk-queries for %s...", WorkMetricsListW)
		    for prc_itr in prc_iter_list:
			slice_dev_id, need_processes = GetDevicesIDLists(KeyList, prc_itr, prc_iter_cnt, max_processes, max_devices_in_process)
			# Список процессов
			my_prcs_W = []
			for t in range(need_processes):
			    # Создание нового класса процесса
			    prcWalk = prcWalkOIDs(devices,slice_dev_id[t],"prcW{}".format(t+1),WorkMetricsListW)
			    # Процесс добавляется в список процессов. Здесь это нужно, чтобы потом корректно отследить завершение процессов через join
			    my_prcs_W.append(prcWalk)
			    prcWalk.start()

			# Перебираем список процессов и ждем, пока все будут завершены
			for prc in my_prcs_W:
			    prc.join()
		    logger.info("INFO: Completed all walk-requests. Elapsed time {:.4f} sec".format(time.time()-qtime))

		if (not walk_before_set and walk_or_set_pass == 1) or (walk_before_set and walk_or_set_pass == 2):
		    # Получаем список метрик на основе номера прохода, который кратен максимальному ключу из набора метрик
		    WorkMetricsListS = PassSet[max([setkey for setkey in PassSet if passnum % setkey == 0])]
		    logger.info("INFO: Sending set-queries for %s...", WorkMetricsListS)
		    for prc_itr in prc_iter_list:
			slice_dev_id, need_processes = GetDevicesIDLists(KeyList, prc_itr, prc_iter_cnt, max_processes, max_devices_in_process)
			# Список процессов
			my_prcs_S = []
			for t in range(need_processes):
			    # Создание нового класса процессов
			    prcSet = prcSetOIDs(devices,slice_dev_id[t],"prcS{}".format(t+1),WorkMetricsListS)
			    # Процесс добавляется в список процессов. Здесь это нужно, чтобы потом корректно отследить завершение процессов через join
			    my_prcs_S.append(prcSet)
			    prcSet.start()

			# Перебираем список потоков и ждем, пока все будут завершены
			for prc in my_prcs_S:
			    prc.join()
		    logger.info("INFO: Completed all set-requests. Elapsed time {:.4f} sec. Going to sleep for {} sec...".format(time.time()-qtime,sleep_after_set_requests))
		    time.sleep(sleep_after_set_requests)


	    # И снова получаем список ключей, отсортированный по времени
	    KeyList = sorted(devices.keys(),key=lambda k: devices[k]['time'])
	    # Формируем словарь метрик, отправляемых в Graphite. Для каждого сервера создаем пустой список.
	    Carbon_Metrics = {}
	    for GraphiteCarbon in GraphiteCarbonList:
		Carbon_Metrics[GraphiteCarbon[1]+':'+str(GraphiteCarbon[2])] = []

	    # Подсчитываем общее число метрик в памяти, а также число метрик, собранных при помощи SNMP
	    total_metric_num = 0
	    snmp_metric_num = 0
	    # Преобразуем devices в обычный словарь. Работа с ним быстрее, чем с multiprocessing.Manager().dict
	    devices = dict(devices)
	    # Перебираем идентификаторы устройств (отсротированные по времени ключи)
	    for dev_id in KeyList:
		# Подсчитываем число метрик, которые были собраны в результате SNMP-опроса
		snmp_metric_num += devices[dev_id]['metrics']
		# Перебираем все параметры для конкретного устройства
		for param in devices[dev_id]['data']:
		    # Подсчитываем общее число метрик в памяти
		    total_metric_num += len(devices[dev_id]['data'][param])
		    # Работаем с параметром, если это не счетчик
		    if (param[0:1] != '~'):
			# Перебираем список серверов Carbon
			for GraphiteCarbon in GraphiteCarbonList:
			    try:
				# Если текущий параметр (метрика) присутствует в исходном списке метрик для данного сервера, добавляем ее в итоговый список метрик этого сервера
				if param in GraphiteCarbon[4]:
				    for subparam in devices[dev_id]['data'][param]:
					# Формируем итоговый список метрик. Используем зарезервированное имя {$device}, которое заменяется на имя модели
					Carbon_Metrics[GraphiteCarbon[1]+':'+str(GraphiteCarbon[2])].append("{}{}.{}.{} {} {}".format(GraphiteCarbon[3].replace('{$device}',devices[dev_id]['mname']),devices[dev_id]['ip'],param,subparam,devices[dev_id]['data'][param][subparam],devices[dev_id]['walk_timestamp']))
			    except:
				logger.info("CRITICAL: Wrong structure of GraphiteCarbonList! Exiting...")
				sys.exit(2)

	    # Сообщаем в лог информацию о количестве собранных метрик
	    logger.info("INFO: Total number of metrics in memory: %s (including %s by last SNMP queries)", total_metric_num, snmp_metric_num)

	    # Данные в Graphite нужно передавать через равномерные интервалы времени. При опросе различного числа метрик в различных проходах данные могут быть готовы к передаче в разное время
	    # Поэтому мы ориентируемся не по моменту готовности данных, а по специальной константе, которая показывает сколько еще времени к моменту передачи должно оставаться до конца интервала опроса
	    # К примеру, при интервале в 300 секунд и константе в 30 секунд, данные начнут передаваться не ранее, чем через 270 секунд от начала опроса. Если данные готовы раньше, то мы просто ждем
	    if (int(time.time()) - timer < query_interval - datasend_right_border):
		logger.info("INFO: For uniform transmission it is necessary to sleep for another %s sec...", (query_interval - datasend_right_border) - (int(time.time()) - timer))
		while (int(time.time()) - timer < query_interval - datasend_right_border):
		    time.sleep(0.1)

	    # Перебираем список серверов Carbon и пробуем отправить данные в каждый из них
	    for GraphiteCarbon in GraphiteCarbonList:
		if GraphiteCarbon[0]:
		    SendDataToCarbon(Carbon_Metrics[GraphiteCarbon[1]+':'+str(GraphiteCarbon[2])], GraphiteCarbon[1], GraphiteCarbon[2])

	    # Подсчитываем пропуски (ошибки) в получении данных. При наличии пропусков сообщаем об этом в лог
	    metric_skipped = 0
	    dev_metr_skipp = 0
	    for dd in devices.copy():
		metric_skipped += devices[dd]['errors']
		dev_metr_skipp += (devices[dd]['errors']>0)
	    if metric_skipped > 0:
		logger.info("WARNING: At least %s metrics was skipped for %s devices", metric_skipped, dev_metr_skipp)

	    # Отправляем статистику в MySQL, если в файле конфигурации включена соответствующая опция
	    if useMySQLstat:
		qtime = time.time()
		SendDataToMySQL(mysql_stat_addr, mysql_stat_user, mysql_stat_pass, mysql_stat_base, mysql_stat_cset, mysql_stat_tabl, KeyList, devices, qtime)

	    logger.info("INFO: ------- Pass №{} completed for {:.4f} sec -------".format(passnum,time.time()-timer))
	    passnum+=1
	time.sleep(sleep_interval)

# ------- Служебный блок: создание и управление демоном -------

class MyDaemon(Daemon):
    def run(self):
        main()

if __name__ == "__main__":
    daemon = MyDaemon('/var/run/briseis.pid','/dev/null', log_file, log_file)
    if len(sys.argv) == 2:
        if   'start'     == sys.argv[1]:
            daemon.start()
        elif 'faststart' == sys.argv[1]:
            daemon.start()
        elif 'stop'      == sys.argv[1]:
            daemon.stop()
        elif 'restart'   == sys.argv[1]:
            daemon.restart()
        else:
            print "Briseis: "+sys.argv[1]+" - unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

# ------- Конец служебного блока -------