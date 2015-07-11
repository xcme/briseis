#!/usr/local/bin/python
#coding=UTF8
#start            (2014.08.10)
#released         (2015.03.05)
#version 1.1.0    (2015.07.11)

import multiprocessing, threading, netsnmp, time, sys, socket, MySQLdb, logging
from    math import ceil
from  daemon import Daemon

from bconfig import logfile, snmp_WComm, snmp_Timeout, snmp_Retries, oid_ModelName
from bconfig import ModelNameRemoveStr, query_interval, sleep_interval, sleep_after_set_requests
from bconfig import set_iter_delay, try_fix_query_errors, max_threads, max_requests_in_thread
from bconfig import max_processes, max_devices_in_process, oids_set, oids_walk, useGraphite
from bconfig import GraphiteCarbonAddress, GraphiteCarbonPort, GraphiteMetricsList
from bconfig import GraphiteCarbonPrefix, useAttractor, AttractorAddress, AttractorPort
from bconfig import AttractorMetricsList, AttractorDupMetric, PassSetSet, PassSetWalk, mysql_addr
from bconfig import mysql_user, mysql_pass, mysql_base, mysql_query_p, useMySQLstat
from bconfig import mysql_stat_addr, mysql_stat_user, mysql_stat_pass, mysql_stat_base
from bconfig import mysql_stat_cset, mysql_stat_tabl

logging.basicConfig(filename = logfile, level = logging.DEBUG, format = '%(asctime)s  %(message)s')

def GetDataFromMySQL(mysql_addr,mysql_user,mysql_pass,mysql_base,mysql_query,comment): # Функция для получения списка устройств из базы MySQL
    global log
    mysql_data=''
    # Пробуем подключиться к базе данных MySQL. Используем таймаут в 2 секунды
    try:
	mysql_db = MySQLdb.connect(host=mysql_addr, user=mysql_user, passwd=mysql_pass, db=mysql_base, connect_timeout=2)
    except MySQLdb.Error as err:
	# Если возникла ошибка при подключении, сообщаем об этом в лог и возвращаем пустой список
	logging.info("ERROR (MySQL): Cannot connect to server '{}': {}".format(mysql_addr,err.args[1]))
	return mysql_data
    else:
	# Если ошибок не было, сообщаем в лог об успешном подключении и создаем 'курсор' (особая, MySQLdb-шная магия)
	logging.info("Connection to MySQL Server '{}' established".format(mysql_addr))
	mysql_cr = mysql_db.cursor()
	# Пробуем выполнить запрос к базе
	try:
	    mysql_cr.execute(mysql_query)
	except MySQLdb.Error as err:
	    # Если возникла ошибка при выполнении запроса, сообщаем об этом в лог и возвращаем пустой список
	    logging.info("ERROR (MySQL): Read-Query '{}' failed: {}".format(comment,err.args[1]))
	    return mysql_data
	else:
	    # Получаем все данные из 'курсора'
	    mysql_data = mysql_cr.fetchall()
	    # Пишем в лог об успешном запросе
	    logging.info("MySQL Read-Query '{}' OK. {} rows found".format(comment,len(mysql_data)))
	    mysql_db.close()
	    # Возвращаем словарь из полученных данных вида 'ip'=>'id'
	    return mysql_data

def Prepare_Devices(dev_tmp): # Функция для подготовки словаря устройств
    dev = {}
    # Создаем ключи словаря:
    for line in dev_tmp:
	dev[line[0]]={}
    for line in dev_tmp:
	# Словарь будет иметь вид {id:{'ip':value, 'wcomm':value,...}}
	dev[line[0]].update({'ip':line[1], 'wcomm':line[2], 'set_timestamp':0, 'walk_timestamp':0, 'skips':0, 'errors':0, 'avail':0, 'queries':0, 'time':0, 'data':{}, 'set_res':{}})
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
		    ip = devline['ip']
		    snmp_comm_this_device = snmp_WComm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm']!='': snmp_comm_this_device = devline['wcomm']
		    start_time = time.time()
		    var = netsnmp.Varbind(oid_ModelName)
		    query = netsnmp.snmpget(var, Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_Timeout, Retries = snmp_Retries, UseNumeric = 1)
		    # Время, затраченное на опрос
		    query_time = int((time.time()-start_time)*1000)
		    # Вырезаем из имени определенные пользователем последовательности. Если ответ не распознан, обрабатываем его как будто он не был получен
		    try:
			mname = str(query[0])
		    except:
			mname = 'None'
			logging.info("{},{},{},{},{}".format(ip,snmp_comm_this_device,oid_ModelName,var,query))
		    for StrToRem in ModelNameRemoveStr:
			mname = mname.replace(StrToRem,"")
		    devline['mname']=mname
		    # Инкрементируем счетчик доступности, если ответ был получен
		    if mname<>'None':
			devline['avail'] += 1
		    # Считаем общее кол-во опросов устройства
		    devline['queries'] += 1
		    devline['time'] += query_time
		    self.devices[id_] = devline

#	logging.info("Process {} started. Processing {} entries...".format(self.prcname,len(self.ids4prc)))
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
		# Имена потоков имеют вид thr1, thr2,. .., thrN
		thrGetD.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_G.append(thrGetD)
		thrGetD.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_G:
		thr.join()
#	logging.info("Process {} finished".format(self.prcname))

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
		    ip = devline['ip']
		    snmp_comm_this_device = snmp_WComm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm']!='': snmp_comm_this_device = devline['wcomm']
		    device_model = devline['mname']
		    if device_model in oids_set:
			query = 'skipped'
			for paramname in sorted(oids_set[device_model].keys()):
			    start_time = time.time()
			    if paramname in self.WorkMetricsListS:
				varlist = netsnmp.VarList(*[netsnmp.Varbind(*VarBindItem) for VarBindItem in oids_set[device_model][paramname]])
				query   = netsnmp.snmpset(*varlist, Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_Timeout, Retries = snmp_Retries, UseNumeric = 1)
				time.sleep(set_iter_delay)
			    # Время, затраченное на опрос
			    query_time = int((time.time()-start_time)*1000)
			    devline['time'] += query_time
			    devline['set_res'][paramname] = query
		    devline['set_timestamp'] = int(time.time())
		    self.devices[id_] = devline

#	logging.info("Process {} started. Processing {} entries...".format(self.prcname,len(self.ids4prc)))
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
		# Имена потоков имеют вид thr1, thr2,. .., thrN
		thrSet.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_S.append(thrSet)
		thrSet.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_S:
		thr.join()
#	logging.info("Process {} finished".format(self.prcname))


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
		    ip = devline['ip']
		    snmp_comm_this_device = snmp_WComm
		    # Если community для устройства задано явно - переопределяем переменную
		    if devline['wcomm']!='': snmp_comm_this_device = devline['wcomm']
		    device_model = devline['mname']
		    for stack_oids in oids_walk:
			start_time = time.time()
			# Объявляем переменную, т.к. если встретится неизвестная модель, то она не будет определена
			varlist = []
			if device_model in stack_oids:
			    Get_notWalk = False
			    for paramname in sorted(stack_oids[device_model].keys()):
				if '.' in paramname:
				    Get_notWalk = True
			    # Номер попытки опроса
			    q_try_num = 0
			    # Отсутствие ошибок опроса. 1 - ошибок нет, 0 - есть. Начальное значение должно быть 0, чтобы выполнился цикл опроса
			    q_noerr = 0
			    # Получаем имя параметра для сравнения со списком набора метрик для опроса. Из '~RX' получим 'RX', из 'CNS..7' получим 'CNS'
			    tmp_param = paramname
			    if '.' in tmp_param:
				tmp_param = tmp_param[0:tmp_param.find('.')]
			    if '~' in tmp_param:
				tmp_param = tmp_param.replace('~','')
			    if (tmp_param in self.WorkMetricsListW):
				# Выполняем опрос пока не исчерпаны попытки и не зафиксировано отсутствие ошибок
				while (q_try_num<=try_fix_query_errors and q_noerr<>1):
				    varlist = netsnmp.VarList(*[ netsnmp.Varbind(stack_oids[device_model][paramname]) for paramname in stack_oids[device_model] ])
				    if Get_notWalk:
					query   = netsnmp.snmpget(*varlist,Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_Timeout, Retries = snmp_Retries, UseNumeric = 1)
				    else:
					query   = netsnmp.snmpwalk(varlist,Version = 2, DestHost = ip, Community = snmp_comm_this_device, Timeout = snmp_Timeout, Retries = snmp_Retries, UseNumeric = 1)
				    q_noerr = int(None not in [ v_item.tag for v_item in varlist ])
				    q_try_num += 1
			# Время, затраченное на опрос
			query_time = int((time.time()-start_time)*1000)
			devline['time'] += query_time
			for var_ in varlist:
			    # Иногда ответ может быть не распознан. В таких случаях фиксируем ошибку
			    if ( (var_.tag is not None) & (var_.iid is not None) ):
				paramkey=var_.tag+'.'+var_.iid # Полный OID
			    else:
				paramkey = ''
				devline['skips'] += 1
			    if ( (device_model in stack_oids) & (paramkey<>'') ) :
				# Здесь k - имя параметра, по которому получим значение, а prep_k - имя ключа в 'data'
				# В случае walk-запроса значения k и prep_k равны, а в случае get имя prep_k обрезается до первой точки, не включая ее
				for k in stack_oids[device_model]:
				    # Если используем метод get, то получаем имя ключа из параметра k с начала до первой точки, не включая ее, и задаем трейлер
				    # Для метода опроса walk имя ключа будет равно параметру k, а трейлер должен быть пустым
				    if Get_notWalk:
					prep_k = k[0:k.find('.')]
					trailer = '*'
				    else:
					prep_k = k
					trailer = ''
				    # Проверяем, есть ли значение параметра в полном OID
				    # Значение trailer прибавляем для избежания ложного срабатывания при сравнении .1.2.3.2 и .1.2.3.20. При Get-запросе трейлер = '*'
				    # Теперь будут сравниваться .1.2.3.2* и .1.2.3.20*. Первое значение уже не входит во второе, чего не скажешь о предыдущем случае
				    # При Walk-запросе трейлер пустой, потому что paramkey будет отличаться от OID из файла конфигурации
				    # Получится. например, .1.2.3.2 и .1.2.3.2.5.100. Здесь вхождение определяется однозначно верно, а трейлер будет мешать
				    if (stack_oids[device_model][k]+trailer in paramkey+trailer):
					# Получаем оставшуюся часть от OID
					remainder=paramkey.replace(stack_oids[device_model][k]+'.','')
					# Если используем метод get, оставшаяся часть будет равна iid
					if Get_notWalk:
					    remainder = var_.iid
					    # Альтернативный вариант для использования двух последних чисел OID в имени подраздела, например '7.100'
					    if '..' in k:
						remainder = ".".join(paramkey.split(".")[-2:])
					# Например в конфиге указан OID 1.2.3.2.1, tag будет 1.2.3.2.1.X, iid - Y (может быть пустым). Полный OID (paramkey) будет 1.2.3.2.1.X.Y
					# Имя раздела (словаря) будет k, а подраздела (ключа метрики) - remainder
					if (prep_k not in devline['data']):
					    devline['data'][prep_k]={}
					# Если работаем со счетчиком:
					if (prep_k[0:1] == '~'):
					    # Если такое имя есть данных, получаем предыдущее значение счетчика
					    if remainder in devline['data'][prep_k]:
						prev_val = devline['data'][prep_k][remainder]
						not_skipped = True
					    # Если такого поля нет, считаем значения равными 0
					    else:
						prev_val = 0
						not_skipped = False
					    new_val = 0
					    # Проверка корректности типов найденных значения счетчиков (+5)
					    if (isinstance(prev_val, int) | isinstance(prev_val, long) | isinstance(prev_val, float)):
						try:
						    new_val = int(var_.val)
						except:
						    pass
					    # ~ - 64-битные счетчики, ~~ - 32-битные
					    if (prep_k[0:2] == '~~'):
						new_k = prep_k[2:]
						pw_ = 32
					    else:
						new_k = prep_k[1:]
						pw_ = 64
					    if new_k not in devline['data']:
						devline['data'][new_k]={}
					    devline['data'][prep_k][remainder] = new_val
					    # Если удалось получить предыдущее значение, то вычисляем разницу
					    if not_skipped:
						new_val = new_val - prev_val
						if new_val < 0:
						    new_val = new_val + (pow(2,pw_)-1)
						devline['data'][new_k][remainder] = new_val
					else:
					    devline['data'][prep_k][remainder] = var_.val
			    # Итак, еще раз: paramkey - полный OID, stack_oids[device_model][k] - OID в конфиге, k - имя параметра для OID в конфиге, например RX_crc
			    # prep_k - имя ключа в 'data', которое при walk равно k, а при get обрезается до точки, т.к. точка в имени указывает на использование get
			    # new_k - новое имя ключа, получаемое из prep_k, где обрезаются начальные символы ~, указывающие на тип 'счетчик'
			    # remainder - имя ключа метрики
		    devline['walk_timestamp'] = int(time.time())
		    self.devices[id_] = devline

#	logging.info("Process {} started. Processing {} entries...".format(self.prcname,len(self.ids4prc)))
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
		# Имена потоков имеют вид thr1, thr2,. .., thrN
		thrWalk.setName("{}thr{}".format(self.prcname,t+1))
		# Поток добавляется в список потоков. Здесь это нужно, чтобы потом корректно отследить завершение потока через join
		my_thrs_W.append(thrWalk)
		thrWalk.start()

	    # Перебираем список потоков и ждем, пока все будут завершены
	    for thr in my_thrs_W:
		thr.join()
#	logging.info("Process {} finished".format(self.prcname))


def main():
    logging.info("Daemon 'Briseis' started...")

    def SendDataToCarbon(data):
	stime = time.time()
	try:
	    sock = socket.create_connection((GraphiteCarbonAddress, GraphiteCarbonPort), timeout=3)
	    sock.settimeout(None)
	except socket.error as s_err:
	    logging.info("ERROR: Cannot connect to Graphite/Carbon ({}:{}): {}".format(GraphiteCarbonAddress, GraphiteCarbonPort, s_err))
	else:
	    logging.info("Connection to Graphite/Carbon ({}:{}) established".format(GraphiteCarbonAddress, GraphiteCarbonPort))
	    try:
		for metric in data:
		    sock.sendall(metric+"\n")
		sock.close()
	    except:
		logging.info("ERROR: Cannot send data to Graphite/Carbon. Something wrong!")
	    else:
		logging.info("{} metrics was send to Graphite/Carbon for {:.4f} sec".format(len(data),time.time()-stime))

    def SendDataToAttractor(data,duplen):
	stime = time.time()
	try:
	    sock = socket.create_connection((AttractorAddress, AttractorPort), timeout=3)
	    sock.settimeout(None)
	except socket.error as s_err:
	    logging.info("ERROR: Cannot connect to Attractor ({}:{}): {}!".format(AttractorAddress, AttractorPort, s_err))
	else:
	    logging.info("Connection to Attractor ({}:{}) established".format(AttractorAddress, AttractorPort))
	    try:
		for metricline in data:
		    sock.sendall(metricline+"\n")
		sock.close()
	    except:
		logging.info("ERROR: Cannot send data to Attractor. Something wrong!")
	    else:
		logging.info("{} metrics was send to Attractor for {:.4f} sec".format(len(data),time.time()-stime))
		if duplen>0:
		    logging.info("Note: Configuration involves duplication Attractor's metrics. Sent number of metrics can be more than prepared.")

    #--
    passnum = 1
    devices = {}
    # Удаление пустых словарей из oids_walk
    while {} in oids_walk:
	oids_walk.remove({})
    timer = int(time.time())
    while True:
	if ((int(time.time()) - timer >= query_interval) or (passnum == 1)):
	    logging.info("-------       Pass №{} processing...        -------".format(passnum))
	    timer = int(time.time())
	    # Получаем id и IP устройств и id моделей из базы
	    devices_tmp = GetDataFromMySQL(mysql_addr,mysql_user,mysql_pass,mysql_base,mysql_query_p,'*Select devices*')
	    # Преобразовываем результат запроса в словарь
	    devices_tmp = Prepare_Devices(devices_tmp)
	    # Список ID устройств, которые отсутствуют в новой выборке
	    removed_devices = list(set(devices.keys())-set(devices_tmp.keys()))
	    # Список ID устройств, которые добавились в новой выборке
	    added_devices   = list(set(devices_tmp.keys())-set(devices.keys()))
	    # Пишем в лог об удаленных устройствах
	    for dev in removed_devices:
		logging.info("(-) Device {}:{} was removed from database".format(dev,devices[dev]['ip']))
	    # При первом запуске пишем в лог общее количество добавленных устройств, а в остальных случаях перечисляем все добавленные
	    if passnum>1:
		for dev in added_devices:
		    logging.info("(+) Device {}:{} was added to database".format(dev,devices_tmp[dev]['ip']))
	    else:
		logging.info("(+++) Added {} devices to database".format(len(devices_tmp)))
	    # В новый словарь добавляем данные о доступности и времени опроса из старого
	    for dev in devices_tmp:
		# Делаем это в случае, если устройство отсутствует в списке добавленных, т.е. работа с ним уже велась
		if dev not in added_devices:
		    devices_tmp[dev]['avail']=devices[dev]['avail']
		    devices_tmp[dev]['queries']=devices[dev]['queries']
		    devices_tmp[dev]['errors']=devices[dev]['errors']
		    devices_tmp[dev]['time']=devices[dev]['time']
		    devices_tmp[dev]['data']={}
		    if 'mname' in devices[dev]:
			device_model = devices[dev]['mname']
			for stack_oids in oids_walk:
			    if device_model in stack_oids:
				for k in stack_oids[device_model]:
				    prep_k = k
				    if '.' in k:
					prep_k = prep_k[0:prep_k.find('.')]
				    if ((k[0:1] == '~') & (prep_k in devices[dev]['data'])):
					devices_tmp[dev]['data'][prep_k]=devices[dev]['data'][prep_k]

	    devices = multiprocessing.Manager().dict(devices_tmp.copy())
	    devices_tmp.clear()

	    for attempt in range(2):
		#При первом проходе обрабатываем все устройства
		if attempt==0: devdict=devices
		# При втором - только те, что не были доступными в первый раз
		if attempt==1: devdict=skipped_devices
		# Узнаем необходимое количество опросов (для процессов)
		prc_iter_cnt  = int(ceil(float(len(devdict))/max_processes/max_devices_in_process))
		# Формируем список от 1 до N, чтобы было удобнее перебирать
		prc_iter_list = map(lambda x: x+1,range(prc_iter_cnt))
		# Получаем список ключей из devdict, отсортированный по времени
		KeyList=sorted(devdict.keys(),key=lambda k: devices[k]['time'])
		qtime = time.time()
		for prc_itr in prc_iter_list:
		    slice_dev_id, need_processes = GetDevicesIDLists(KeyList,prc_itr,prc_iter_cnt,max_processes,max_devices_in_process)
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
		logging.info("Polling devices from the database. Attempt #{} of 2 completed for {:.4f} sec".format(attempt+1,time.time()-qtime))
		skipped_dev_cnt = 0
		skipped_devices = {}
		for d in devices.copy():
		    if devices[d]['mname']=='None':
			skipped_dev_cnt += 1
			skipped_devices[d]=devices[d]
		if skipped_dev_cnt>0:
		    logging.info("WARNING: Found {} offline devices for #{} iteration!".format(skipped_dev_cnt,attempt+1))

	    devices_tmp = devices.copy()
	    for dev in devices.copy():
		if devices[dev]['mname']=='None':
		    del devices_tmp[dev]
	    devdict = devices_tmp
	    # Узнаем необходимое количество опросов (для процессов)
	    prc_iter_cnt  = int(ceil(float(len(devdict))/max_processes/max_devices_in_process))
	    # Формируем список от 1 до N, чтобы было удобнее перебирать
	    prc_iter_list = map(lambda x: x+1,range(prc_iter_cnt))
	    # Получаем список ключей из devdict, отсортированный по времени
	    KeyList   = sorted(devdict.keys(),key=lambda k: devices[k]['time'])
	    qtime = time.time()
	    WorkMetricsListS = PassSetSet[(passnum-1)%len(PassSetSet)+1]
	    logging.info("Sending set-queries for {}...".format(WorkMetricsListS))
	    for prc_itr in prc_iter_list:
		slice_dev_id, need_processes = GetDevicesIDLists(KeyList,prc_itr,prc_iter_cnt,max_processes,max_devices_in_process)
		# Список процессов
		my_prcs_S = []
		for t in range(need_processes):
		    # Создание нового класса процессов
		    prcSet = prcSetOIDs(devices,slice_dev_id[t],"prcS{}".format(t+1),WorkMetricsListS)
		    # Ппроцесс добавляется в список процессов. Здесь это нужно, чтобы потом корректно отследить завершение процессов через join
		    my_prcs_S.append(prcSet)
		    prcSet.start()

		# Перебираем список потоков и ждем, пока все будут завершены
		for prc in my_prcs_S:
		    prc.join()
	    logging.info("Completed all set-requests. Elapsed time {:.4f} sec. Going to sleep for {} sec...".format(time.time()-qtime,sleep_after_set_requests))
	    time.sleep(sleep_after_set_requests)

	    # Получаем список ключей из devdict, отсортированный по времени
	    KeyList   = sorted(devdict.keys(),key=lambda k: devices[k]['time'])
	    qtime = time.time()
	    WorkMetricsListW = PassSetWalk[(passnum-1)%len(PassSetWalk)+1]
	    logging.info("Sending get/walk-queries for {}...".format(WorkMetricsListW))
	    for prc_itr in prc_iter_list:
		slice_dev_id, need_processes = GetDevicesIDLists(KeyList,prc_itr,prc_iter_cnt,max_processes,max_devices_in_process)
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
	    logging.info("Completed all walk-requests. Elapsed time {:.4f} sec".format(time.time()-qtime))

	    KeyList = sorted(devices.keys(),key=lambda k: devices[k]['time'])
	    carbon_metrics = []
	    attractor_metrics = []
	    total_metric_num = 0
	    devices = dict(devices)
	    for dev_id in KeyList:
		for param in devices[dev_id]['data']:
		    total_metric_num += len(devices[dev_id]['data'][param])
		    if (param[0:1]<>'~'):
			if param in GraphiteMetricsList:
			    for subparam in devices[dev_id]['data'][param]:
				carbon_metrics.append("{}{}.{}.{} {} {}".format(GraphiteCarbonPrefix,devices[dev_id]['ip'],param,subparam,devices[dev_id]['data'][param][subparam],devices[dev_id]['walk_timestamp']))
			# Если параметр (метрика) есть в списке метрик, передаваемых в анализатор:
			if param in AttractorMetricsList:
			    for subparam in devices[dev_id]['data'][param]:
				attractor_metrics.append("{{'metric':'{0}','device':'{1}','host':'{2}','key':'{3}','value':'{4}','timestamp':'{5}'}}".format(
				    param,devices[dev_id]['mname'],devices[dev_id]['ip'],subparam,devices[dev_id]['data'][param][subparam],devices[dev_id]['walk_timestamp']))
				# Если параметр (метрика) есть в словаре дубликатов метрик, создаем необходимые дубликаты
				if param in AttractorDupMetric:
				    for dup in AttractorDupMetric[param]:
					attractor_metrics.append("{{'metric':'{0}','device':'{1}','host':'{2}','key':'{3}','value':'{4}','timestamp':'{5}'}}".format(
					    dup,devices[dev_id]['mname'],devices[dev_id]['ip'],subparam,devices[dev_id]['data'][param][subparam],devices[dev_id]['walk_timestamp']))
	    logging.info("Total number of metrics in memory: {}".format(total_metric_num))
	    if useGraphite:
		SendDataToCarbon(carbon_metrics)
	    if useAttractor:
		SendDataToAttractor(attractor_metrics,len(AttractorDupMetric))
	    metric_skipped = 0
	    dev_metr_skipp = 0
	    for dd in devices.copy():
		if devices[dd]['skips']>0:
		    metric_skipped += devices[dd]['skips']
		    devices[dd]['errors'] += devices[dd]['skips']
		    dev_metr_skipp +=1
	    if metric_skipped>0:
		logging.info("At least {} metrics was skipped for {} devices".format(metric_skipped,dev_metr_skipp))
	    if useMySQLstat:
		qtime = time.time()
		try:
		    mysql_stat_conn = MySQLdb.connect(host=mysql_stat_addr, user=mysql_stat_user, passwd=mysql_stat_pass, db=mysql_stat_base, charset=mysql_stat_cset, connect_timeout=1)
		    mysql_stat_conn.autocommit(True)
		except MySQLdb.Error as err:
		    logging.info("ERROR (MySQL): Cannot connect to statistics server '{}': {}".format(mysql_stat_addr,err.args[1]))
		else:
		    logging.info("Connection to MySQL statistics Server '{}' established".format(mysql_stat_addr))
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
			send_query['query']  = "INSERT INTO {0}.{1} ({1}.device_id,{1}.host,{1}.mname,{1}.set_timestamp,{1}.walk_timestamp,{1}.avail,{1}.queries,{1}.errors,{1}.time) VALUES ".format(mysql_stat_base,mysql_stat_tabl)
		    send_query['query'] += "('{0}','{1}',SUBSTR('{2}',1,16),'{3}','{4}',{5},'{6}','{7}','{8}'),".format(dev_id,devices[dev_id]['ip'],devices[dev_id]['mname'],devices[dev_id]['set_timestamp'],devices[dev_id]['walk_timestamp'],devices[dev_id]['avail'],devices[dev_id]['queries'],devices[dev_id]['errors'],devices[dev_id]['time'])
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
		logging.info("Sended {} entries to statictics server. Elapsed time {:.4f} sec".format(send_query['total'],time.time()-qtime))

	    logging.info("------- Pass №{} completed for {:.4f} sec -------".format(passnum,time.time()-timer))
	    passnum+=1
	time.sleep(sleep_interval)

# ------- Служебный блок: создание и управление демоном -------

class MyDaemon(Daemon):
    def run(self):
        main()

if __name__ == "__main__":
    daemon = MyDaemon('/var/run/briseis.pid','/dev/null',logfile,logfile)
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