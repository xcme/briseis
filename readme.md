**Briseis** - мощный, гибкий и быстрый инструмент для сбора метрик с устройств в сети по протоколу SNMPv2. Написанный на Python и представленный в виде Unix-демона, он позволяет собирать большие объемы данных в несколько потоков и передавать их в Graphite и анализатор метрик Attractor. Этот инструмент будет полезен, прежде всего, сетевым администраторам.

##Возможности Briseis
- Получение большого количества метрик за небольшой интервал времени
- Установка заранее определенных значений объектам SNMP (операция snmpset)
- Отправка произвольно выбранных метрик в базу Graphite (Carbon)
- Отправка произвольно выбранных метрик в анализатор метрик Attractor

##Особенности
- Работа системным сервисом (daemon)
- Гибкая система конфигурирования, возможность задавать метрики, группировать их, задавать их тип и способ опроса
- Отсутствие привязки к конкретному оборудованию или вендору
- Многопоточный опрос устройств, собирающий информацию с нескольких устройств одновременно
- Запуск нескольких дочерних процессов, каждый из которых может выполнять многопоточный опрос
- Возможность собрать bulk-запрос, для уменьшения общего количества транзакций
- Проверка устройств на доступность: опрос производится только для доступных в данный момент устройств
- Сортировка устройств в памяти по времени отклика: самые медленные устройства опрашиваются последними, самые быстрые - первыми
- Ведение статистики по доступности устройств и времени отклика

##Требования
- FreeBSD (для работы системным демоном)
- Python + MySQLdb. По умолчанию подразумевается, что Python доступ по адресу '*/usr/local/bin/python*'. При необходимости надо поправить путь в файлах 'briseis', 'briseis.py' и 'daemon.py'.
- Net-SNMP
- Доступ к вашему MySQL-серверу для получения списка устройств и для отправки статистики (опционально)

##Предназначение
Для начала определимся, что такое подразумевается под метрикой:

- При конфигурировании это имя некоторого свойства объекта, например *RX_crc*, для которого мы прописываем соответствующий ему идентификатор - OID
- После завершения опроса устройства это имя вида *host.metric.key*, которому соответствует некоторое значение *value*.

Поскольку изначально **Briseis** разрабатывалась для опроса сетевых коммутаторов, приведу пример из этой области. Если для определенного коммутатора *host* мы снимаем метрику *RX_crc*, то можем собрать такую метрику с каждого порта. Значению *key* в этом случае будет соответствовать номер порта, а значению *value* - полученное значение при опросе. Значения *key* и *value*  определяются автоматически. Например, в соответствующем месте конфигурации мы определяем имя метрики и соответствующий OID - '*RX_crc*':*'.1.3.6.1.2.1.16.1.1.1.8'*.
При выполнения опроса по данному OID программа получит некоторый список:
```
.1.3.6.1.2.1.16.1.1.1.8.1 = Counter32: 84
.1.3.6.1.2.1.16.1.1.1.8.2 = Counter32: 0
...
.1.3.6.1.2.1.16.1.1.1.8.28 = Counter32: 0
```
Каждому порту соответствует определенное значение счетчика. Если из полученного *tag* вычесть указанный в конфигурации OID то получится тот самый *key* ('*.1.3.6.1.2.1.16.1.1.1.8.28*' - '*.1.3.6.1.2.1.16.1.1.1.8*' = '**.28**'). Предположим, что мы опрашивали коммутатор *10.90.90.95*, тогда наши метрики будут иметь следующий вид:
```
10.90.90.95.RX_crc.1 = 84
10.90.90.95.RX_crc.2 = 0
...
10.90.90.95.RX_crc.28 = 0
```
В таком виде метрики и будут отправлены в **Graphite** и **Attractor**.

Теперь, когда мы разобрались, что имеется ввиду под метрикой, пришло время разобраться, что можно с ними делать при помощи **Briseis**. А делать можно вот что:

- Менять значение определенной метрики (свойства), выполняя операцию **snmpset**. Определив *tag*, *iid*, *val* и *type* (см. структуру Varbind в документации по SNMP) как *['.1.3.6.1.4.1.171.12.58.1.1.1.12', '7','1','INTEGER']* мы запишем значение *1* с типом *INTEGER* по адресу *.1.3.6.1.4.1.171.12.58.1.1.1.12.7* На нашем коммутаторе это приведет к диагностике кабельной линии в порту *№7*. Аналогичным образом, определяя нужные значения, можно заставлять устройство сохранять или обновлять конфигурацию, сохранять настройки, выгружать лог-файлы и т.п.
- Получать значение конкретного OID, используя **snmpget**. В этом случае будет выполнен "точечный" запрос, который вернет только одно значение для конкретной метрики.
- Получать "ветку" значений, используя **snmpwalk**. В этом случае (см. пример выше с *RX_crc*) будет возвращен список значений для каждого OID, расположенного в пределах указанного адреса. Для этого осуществляется "перебор" всей "ветки", так как для получения каждого значения отправляется новый запрос.
- Получать несколько значений, используя **getbulk**. Метод отличается от предыдущего тем, что все OID указаны заранее и отправляются в одном запросе. Это может использоваться для исключения ненужных данных из опрашиваемой ветки и для уменьшения общего количества сетевых транзакций.
- Получать метрику как **счетчик**, то есть разницу между текущим и предыдущим значением. Для этого результат для каждой метрики должен быть получен минимум дважды.

Для лучшего понимания этих моментов рекомендую ознакомиться с документацией по SNMP. **Briseis** использует только стандартные методы SNMP, понимая которые будет проще понять логику работы программы.

После того как метрики получены, можно выбрать те из них, которые будут отправлены в **Graphite** и/или в **Attractor**. Для этого существуют списки, где перечисляются имена метрик, отправляемые в конкретную систему. Пример списка: *['RX_crc','RX','TX']*.

Для операций **set** и **get/walk/bulk** существуют отдельные наборы метрик. Каждый такой набор представляет собой словарь или список, который может содержать словари, в свою очередь, содержащие списки метрик.  
Существуют наборы, определяющие метрики для конкретной итерации. Например, можно сделать, чтобы счетчики *RX* и *TX* собирались каждый цикл опроса, а некоторые другие параметры - только в определенный цикл.

Предположим, что мы имеем большой парк коммутаторов, скажем 5000. Используя **Briseis** мы сможем решать следующие задачи:

- Собирать счетчики трафика с интерфейсов устройств
- Периодически сохранять конфигурацию устройств
- Выгружать на внешний TFTP сервер логи устройств или их конфигурацию
- Собирать счетчики ошибок со всех интерфейсов
- Собирать значения длин кабелей "последней мили"\*
- Получать значения аптайма устройств
- Получать состояния интерфейсов (заданная скорость, фактическая скорость, статус интерфейса, состояние интерфейса) и т.п.

Список можно продолжать. Полученные данные мы можем отправить в **Graphite** для отрисовки графиков и анализа, и, параллельно, в **Attractor**, для поиска аномалий.

\*Диагностика кабельной линии может иметь побочные последствия, такие как выключение порта на момент опроса или сбой в логике его работы. Для оборудования *D-Link* я рекомендую использовать диагностику только в корпоративных сетях (не в сетях провайдеров) и только на 100 Мбитных портах.

##Принцип работы
**Briseis** работает следующим образом:

1. Через определенный пользователем интервал обновляет из базы данных MySQL список устройств для опроса. Запрос в MySQL должен возвращать таблицу вида '*id*','*ip*','*write_community*'.
2. Определяет модель для каждого устройства при помощи **snmpget**. Здесь и далее каждый опрос производится в несколько потоков, порождаемых несколькими процессами.
3. Пытается проделать то же самое для устройств, которые не ответили при предыдущей попытке опроса. Далее работа выполняется только с устройствами, которые ответили на запрос, т.е. доступны в данный момент.
4. Для каждого активного устройства выполняет операции **snmpset** для данной модели (если они заданы).
5. Выжидает короткий интервал, определенный пользователем.
6. Для каждого активного устройства выполняет операции **snmpwalk** для данной модели (если они заданы).
7. Помещает собранные метрики в **Graphite** (Carbon) или **Attractor**.
8. Отправляет в базу данных MySQL статистику последнего опроса. Старая статистика при этом очищается. В статистику отправляется фактическая модель устройств, время завершения опроса и его длительность, процент доступности устройств.

Сам опрос реализован так:

- После каждого опроса **Briseis** запоминает для каждого устройства время, затраченное на получение всех данных.
- Перед каждым новым опросом программа сортирует в памяти список устройств на основе затраченного времени. Самые быстрые устройства опрашиваются первыми.
- Опрос производится в *X* процессов. Каждый процесс порождает *Y* потоков. Каждый поток опрашивает *Z* устройств. Эти величины настраиваются.


##Предварительное тестирование
Для работы с программой очень желательно иметь практический опыт работы сетевым оборудованием по SNMP. **Briseis** - это программа для автоматизации сбора метрик. Это подразумевает, что каждую необходимую вам метрику вы должны уметь получить вручную. При этом вы должны представлять как и в каком виде будет отправлен запрос, сколько сетевых транзакцией это потребует и сколько времени займет, какую нагрузку создаст на устройство. Понимание этих вещей позволит вам оптимальным образом сконфигурировать программу. При больших объемах устройств и метрик даже небольшая неточность может вылиться в существенные временные затраты на проведение опроса или загрузить CPU на вашем оборудовании.

Начните с малого - опросите одну метрику для одного устройства. Убедитесь (см. лог программы), что общее количество полученных метрик и количество метрик, отправленных в **Graphite** и в **Attrtactor**, соответствуют вашим ожиданиям. В этом может помочь прилагаемый в комплекте простой инструмент "**expmetr**". После этого увеличьте число метрик и устройств и проведите проверку еще раз. Отобразите важные для вас параметры из лог файла на графиках вашей системы мониторинга. После этого систему можно запускать в работу по всей сети.

Вы должны понимать, что есть существенный риск повредить вашу сеть или базу данных при неправильной настройке программы.


##Конфигурирование
###Описание параметров в файле **bconfig.py**
Параметр | Описание
- | -
snmp_WComm | SNMP write-community.
snmp_Timeout | Таймаут ожидания ответа
snmp_Retries | Количество попыток получения ответа. Значение "1" означает, что будет предпринята 1 дополнительная попытка опроса, т.е. всего опросов будет 2.

Параметр | Описание
- | -
max_processes | Максимально возможное количество дочерних процессов.
max_devices_in_process | Максимальное количество устройств, обрабатываемых процессом. Если у вас 1000 устройств и вы планируете работу с двумя процессами, ставьте 500-600 (больше половины) - не ошибетесь.
max_threads | Максимально возможное количество потоков.
max_requests_in_thread | Максимальное количество запросов в потоке. Под этим нужно понимать количество устройств, опрашиваемых одновременно.

С помощью этих параметров мы можем указать, что хотим работать с *3* дочерними процессами, каждый из которых может запускать до *10* потоков, а каждый из этих потоков принимает на обработку до *12* устройств за раз. Манипуляция этими параметрами необходима если у вас большая сеть и при этом вы ходите собирать данные очень быстро. К примеру, хорошей практикой для отрисовки значений *RX/TX* является выбор интервала в *5* минут. Это значит, что программа должна полностью выполнить свою работу быстрее, чем за *5* минут. При этом мы столкнемся со следующими трудностями:

- Опрашивая устройства последовательно, мы будем тратить много времени на ожидание поступления данных по сети. Миллисекунды складываются в бесконечность. :)
- Запустив слишком много потоков одновременно мы можем полностью загрузить ядро процессора, увеличив тем самым время работы программы.
- Добавив еще процессов (по сути - ядер, т.к. новому процессу система может назначить другое ядро) можем резко увеличить число потоков и получить переполнение сокетов и ошибку вида "*kernel: sonewconn: pcb 0xfffff80075b06000: Listen queue overflow: 25 already in queue awaiting acceptance*" (для FreeBSD)

Наблюдая за работой программы можно подобрать оптимальные значения параметров чтобы не перегружать систему и в то же время быстро собирать данные.

Параметр | Описание
- | -
logfile | Имя файла журнала.
ModelNameRemoveStr | Список строк, которые будут удалены из строки **ModelName** (шаги №2 и №3 в опросе) для получение удобочитаемого имени устройства. Задается как обычный список Python, например *['str1',' str2',...]*.
query_interval | Интервал, через который начинается новый цикл опроса (см. шаги выполнения программы).
sleep_interval | Пауза между проверками текущего состояния. Поскольку проверка выполняется в бесконечном цикле отсутствие паузы приведет к 100% загрузке CPU.
sleep_after_set_requests | Пауза, которую нужно выдержать после отправки **snmpset**-запросов. После такой команды устройство может быть занято ее выполнением, для этого и предусмотрена пауза перед дальнейшим опросом.
try_fix_query_errors | Число попыток для перезапроса данных, если есть подозрение на ошибку в них. Ошибка, по-видимому, связана с самим Python и модулем net-snmp. В процессе написания программы после очередной оптимизации кода ошибки перестали появляться, но механизм их устранения остался.

Параметр | Описание
- | -
mysql_addr | Адрес MySQL-сервера, откуда будет забираться список устройств для опроса.
mysql_user | Имя пользователя.
mysql_pass | Пароль.
mysql_base | Имя базы данных.
mysql_query_p | Запрос к базе данных для получения списка устройств. Запрос в MySQL должен возвращать таблицу вида 'id','ip','write_community'.

Параметр | Описание
:- | :-
useMySQLstat | Параметр, определяющий будет ли использоваться запись статистики в MySQL. Может принимать значения True и False.
mysql_stat_addr | Адрес MySQL-сервера, куда будет сохраняться статистика.
mysql_stat_user | Имя пользователя.
mysql_stat_pass | Пароль.
mysql_stat_base | Имя базы данных.
mysql_stat_cset | Используемая кодировка.
mysql_stat_tabl | Имя таблицы статистики.

Параметр | Описание
:- | :-
useGraphite | Параметр, определяющий будет ли осуществляться отправка данных в **Graphite** (Carbon). Может принимать значения True и False.
GraphiteCarbonAddress | Адрес carbon-сервера.
GraphiteCarbonPort | TCP-порт carbon-сервера.
GraphiteMetricsList | Список метрик, отправляемых в Graphite. Задается как обычный список Python, например *['RX','TX']*.
GraphiteCarbonPrefix | Префикс для имени метрик. Используется исключительно для удобства формирования файловой структуры на сервере Graphite. Если префикс содержит точку и называется, например 'test.', то все метрики на сервере Graphite будут попадать в папку 'test'.

Параметр | Описание
:- | :-
useAttractor | Параметр, определяющий будет ли осуществляться отправка данных в **Attractor**. Может принимать значения True и False.
AttractorAddress | Адрес Attractor-сервера.
AttractorPort | TCP-порт Attractor-сервера.
AttractorMetricsList | Список метрик, отправляемых в Attractor. Задается как обычный список Python, например *['CNS','RX_crc','DS']*.
AttractorDupMetric | Список метрик для Attractor'а, для которых создается копия. Это может понадобится, если требуется проверить метрику несколько раз по разным независимым условиям. Задается как словарь, где имени копируемой метрики соответствует список новых имен, например *{'P1L':['P1L\*'],'DS':['DS\*','DS#']}*. В данном примере появится дополнительная метрика *'P1L\**', копирующая метрику '*P1L*' и две метрики '*DS\**' и '*DS#*', копирующие метрику '*DS*'.

Параметр | Описание
:- | :-
PassSetSet | Набор метрик для **set**-операций, где ключом является номер операции, а значением имя метрики или набора метрик. При каждой новой итерации программы обрабатывается следующий по порядку номер. Если достигнут конец словаря, отсчет начинается с начала. Набор задается как словарь списков Python, например *{1:[],2:['InitCableDiag'],}*. В данном случае каждая нечетная **set**-операция будет пустой, а при каждой четной будет инициализирована диагностика кабеля.
PassSetWalk | Набор метрик для **walk**-операций, где ключом является номер операции, а значением имя метрики. При каждой новой итерации программы обрабатывается следующий по порядку номер. Если достигнут конец словаря, отсчет начинается с начала. Набор задается как словарь списков Python, например *{1:['RX','TX',],2:['RX','TX','DS',],}*. В данном случае при каждой нечетной операции будут опрашиваться метрики *RX* и *TX*, а при каждой четной - *RX*, *TX* и *DS*.
oid_ModelName | OID для определения имени модели. По умолчанию равен "*.1.3.6.1.2.1.1.1.0*" и соответствует *sysDescr*.

Параметр | Описание
:- | :-
oids_set | Набор метрик, соответствующих OID, ключей и значений для **set**-операций. '**oids_set**' представляет собой "словарь(1) словарей(2) списков(3) списков(4)" и имеет следующий формат:
```
{
'device_model1':{'query1_name':[ [tag1,iid1,val1,type1],[tag2,iid2,val2,type2],...,[tagN,iidN,valN,typeN] ],'query2_name':[...]},
'device_model2':{...}
}
```
**[tag,iid,val,type]** - список(4) необходимых для snmpset параметров:

Параметр | Описание
:- | :-
tag | fully qualified, dotted-decimal, numeric OID
iid | the dotted-decimal, instance identifier
val | the SNMP data value
type | SNMP data type

Пример: **['.1.3.6.1.2.1.17.7.1.4.3.1.2','777','\x00\x00\x00\xf0\x00\x00\x00\x00','OCTETSTR']**  
Эквивалентая команда: **snmpset -v2c -c <WComm> <IP> .1.3.6.1.2.1.17.7.1.4.3.1.2.777 x 000000f000000000**

**query#_name** - имя списка(3) объектов/списков(4), обрабатываемых за один раз. Это означает, что **snmpset**-команды для всех перечисленных объектов будут отправлены одновременно в одном пакете **set-request**. Это может использоваться для экономии времени либо определяться требованиями оборудования для управления конкретными объектами.  
*Пример*: Вы работаете с VLAN, для которого указываете имя, список портов и код операции. Команды, отправленные в одном пакете, будут выполнены, а те же самые команды, отправленные последовательно - проигнорированы. Так происходит потому, что когда устройство получает, например, список портов, оно не знает, к какому VLAN их следует применить, т.к. в этом пакете нет других данных.

**device_model#** - имя словаря(2), содержащего списки объектов(3). При опросе для каждого устройства определяется значение **oid_ModelName**, после чего из него удаляются значения списка **ModelNameRemoveStr**. Если то, что осталось, идентично значению ключа **device_model**, то для данного устройства обрабатываются все **query#_name**, являющиеся значениями данного ключа.

Все это собирается в общий словарь(1) **oids_set**.

*Пример*:
```
oids_set={
    'DES-3200-28':{
        'InitCableDiag':InitCableDiag24
    },
    'DES-3028':{
        'InitCableDiag':InitCableDiag24
    }
}

```
При этом:
```
InitCableDiag24 = [
    ['.1.3.6.1.4.1.171.12.58.1.1.1.12', '1','1','INTEGER'],
    ['.1.3.6.1.4.1.171.12.58.1.1.1.12', '2','1','INTEGER'],
...
    ['.1.3.6.1.4.1.171.12.58.1.1.1.12','24','1','INTEGER'],
]
```
Например, при опросе для некоего устройства для **oid_ModelName** вернулось значение "*D-Link DES-3028 Fast Ethernet Switch*", после удаления из которого содержимого **ModelNameRemoveStr** ('*D-Link *','* Fast Ethernet Switch*') осталось "**DES-3028**". В дальнейшем в программе это используется как имя устройства (**mname**). При разборе словаря **oids_set** ключу '**DES-3028**' соответствует словарь *{'InitCableDiag':InitCableDiag24}*, где имени '*InitCableDiag*' соответствует список *InitCableDiag24*, содержащий списки *tag*, *iid*, *val* и *type*. Все, что находится внутри '*InitCableDiag*' будет упаковано в один **set-request** пакет. Имя '*InitCableDiag*' можно использовать в наборе **set**-операций **PassSetSet**.

Параметр | Описание
:- | :-
oids_walk | Набор метрик и соответствующих OID для **walk**-операций. '**oids_walk**' представляет собой "список(1) словарей(2) словарей(3)" и имеет следующий формат:
```
[{
'device_model1':{'metric_name1':'metric_oid1','metric_name2':'metric_oid2',}
'device_model2':{'metric_name1':'metric_oid1','metric_name2':'metric_oid2',}
},
{
'device_model1':{'metric_name3':'metric_oid3','metric_name4':'metric_oid4',}
'device_model2':{'metric_name3':'metric_oid3','metric_name4':'metric_oid4',}
}
]
```

**{'metric_name1':'metric_oid1','metric_name2':'metric_oid2',}** - словарь(3) соответствий имен метрик и их OID.

**device_model#** - имя словаря(2), содержащего словари объектов(3). При опросе для каждого устройства определяется значение **oid_ModelName**, после чего из него удаляются значения списка **ModelNameRemoveStr**. Если то, что осталось, идентично значению ключа **device_model**, то при каждом таком совпадении для данного устройства обрабатываются все значения данного ключа.

Все это собирается в общий список(1) **oids_walk**.

*Пример*:
```
oids_walk=[{
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
}
]
```
При этом:
```
Errors28 = {
    'RX_crc.1':'.1.3.6.1.2.1.16.1.1.1.8.1',
    'RX_crc.2':'.1.3.6.1.2.1.16.1.1.1.8.2',
...
    'RX_crc.28':'.1.3.6.1.2.1.16.1.1.1.8.28',
}
```

Для каждого элемента списка проверяется соответствие полученного имени устройства (*mname*) и ключа словаря. Если соответствие обнаружено, то для каждого такого ключа определяется соответствующее ему значение, которое является словарем(3). Дальше возможны два варианта:

- Если в имени хотя бы одной из метрик словаря(3) присутствует **точка**, то все содержимое упаковывается в **get-request**.
- Если **точка** отсутствует в именах метрик словаря(3), то все содержимое упаковывается в **walk-request**.

***Это принципиальный для понимания логики работы программы момент***. Предположим, что мы хотим получить значения *ifHCInOctets* (RX, 64 bit) с портов устройства. Мы можем создать словарь(3) *Rx* = *{'~RX':'.1.3.6.1.2.1.31.1.1.1.6'}*. Поскольку точка в имени метрики '*~RX*' отсутствует, программа отправит **walk**-запрос и переберет указанный OID. Аналогично мы можем поступить и с *ifHCOutOctets* (TX, 64bit), создав еще один словарь(3) *Tx* = *{'~TX':'.1.3.6.1.2.1.31.1.1.1.10',}*. При этом в словаре(2) мы укажем сначала первый словарь(3), а потом второй, т.е. получится вот так:
```
oids_walk=[{
    'DES-3200-28':Rx,
},
    {
    'DES-3200-28':Tx,
}
]
```

Обратите внимание, что словари(3) у нас содержат всего по одному элементу. Сначала программа выполняет **walk** для словаря(3) *Rx*, затем, перебирая список(1), делает то же самое для словаря(3) *Tx*. Также обратите внимание на то, что внутри словаря(2) мы указываем каждое имя устройства (*mname*) только один раз. Попросту потому, что словарь не может содержать несколько одинаковых ключей. Если нам требуется задать для этого же типа устройств и другие значения, их следует помещать в другой словарь(2). Именно поэтому все словари(2) потом объединяются в список(1) - чтобы для каждого типа устройств можно было выполнять несколько различных операций.

Теперь, когда мы окончательно запутались, приступим к разбору нюансов. :) Мы знаем, что **walk**-запрос по сути является последовательным перебором значений. Когда при переборе получено значение *tag*, выходящее за пределы заданного OID, перебор считается законченным. Каждый запрос - это сетевая транзакция, требующая некоторого времени. Чем больше транзакций в сети, тем больше мы ждем и тем выше вероятность случайных потерь данных. Поэтому мы можем пойти на хитрость - опрашивать *Rx* и *Tx* одновременно. Для этого создадим единый словарь(3) - *RxTx* = *{'~RX':'.1.3.6.1.2.1.31.1.1.1.6','~TX':'.1.3.6.1.2.1.31.1.1.1.10',}* и укажем его один раз:
```
oids_walk=[{
    'DES-3200-28':RxTx,
},
]
```

Теперь внутри **walk**-запроса мы будем перебирать сразу два адреса одновременно. При этом количество транзакций уменьшится вдвое. Единственное условие здесь - опрашиваемые ветки должны быть одинаковой длины (что очевидно при опросе таких значений как *Rx* и *Tx*, но вовсе не очевидно в других случаях), т.к. опрос будет прекращен при выходе за пределы одной из веток.

Но можно пойти и дальше. Мы можем переделать запрос как **get**, явно указав конкретные OID для конкретных интерфейсов. Теперь наш словарь(3) будет выглядеть так:
```
RxTx28 = {
    '~RX.1' :'.1.3.6.1.2.1.31.1.1.1.6.1',
    '~RX.2' :'.1.3.6.1.2.1.31.1.1.1.6.2',
...
    '~RX.28':'.1.3.6.1.2.1.31.1.1.1.6.28',
    '~TX.1' :'.1.3.6.1.2.1.31.1.1.1.10.1',
    '~TX.2' :'.1.3.6.1.2.1.31.1.1.1.10.2',
...
    '~TX.28':'.1.3.6.1.2.1.31.1.1.1.10.28',
}
```

Здесь мы задаем в качестве ключей словаря(3) разные имена, но лишь потому, что не можем задать одно. Имя метрики в любом случае обрезается до точки, т.е. в итоге мы получаем либо '*RX*', либо '*TX*'. В полном имени метрики после краткого имени метрики будет добавлен ключ, как уже было рассказано выше.
Наш список будет выглядеть как и в предыдущем случае:
```
oids_walk=[{
    'DES-3200-28':RxTx,
},
]
```
Теперь наш запрос превращается в **getBulk** и содержит все необходимые адреса сразу. В итоге мы отправляем всего лишь один запрос и получаем всего лишь один ответ, получая при этом сразу 56 значений!  
**Важно**: **В конечном итоге полные имена метрик никак не зависят от того, как именно мы формируем наши словари. Изменение словарей влияет на то, что именно мы собираем и как мы это делаем, а не на то, как это будет выглядеть после сбора данных.**

##Модификаторы в именах метрик
Имена метрик могут содержать модификаторы, определяющие поведение программы по отношению к этим метрикам.

Модификатор | Описание
:- | :-
'.' | меняет тип запроса с **walk** на **get**. Пример подробно разбирали выше.
'..' | меняет тип запроса с **walk** на **get** и при этом помещает в полное имя метрики дополнительное число из OID. Некоторые OID могут иметь индекс, который увеличивает длину OID, тем самым смещая наш *key*. Оборудование *D-Link* может возвращать для интерфейсов индекс, указывающий на тип используемой среды (медь или оптика). К примеру, мы можем получить вот такой OID - '*.1.3.6.1.4.1.171.11.113.1.3.2.2.2.1.4.1.100*' для порта *№1* и '*.1.3.6.1.4.1.171.11.113.1.3.2.2.2.1.4.2.100*' для порта *№2*. Используя модификатор '..' мы поместим в key уже не '*100*' в обоих случаях, а '*1.100*' в первом случае и '*2.100*' во втором.
'~' | 64-битный счетчик. Выше в примерах мы использовали имена '*~RX*' и '*~TX*'. Такие метрики хранятся в памяти программы как служебные. Когда метрики будут опрошены второй раз, для каждой метрики будет посчитана разница между текущим и предыдущим значением. Так в памяти появятся еще две метрики, представляющие собой счетчики - '*RX*' и '*TX*'. Именно эти метрики и будут отправлены в **Graphite** и **Attractor**.
'~~' | 32-битный счетчик. Остальное аналогично 64-битному.

##Описание файла userdict.py
Этот файл нужен исключительно для удобства визуального восприятия основного файла конфигурации. Сюда можно выносить пользовательские словари и списки, используемые затем внутри **oids_set** и **oids_walk**. Имена этих словарей и списков задаются произвольно. Важно лишь, чтобы не менялась итоговая структура **oids_set** и **oids_walk**.

##Поддерживаемые по умолчанию метрики и устройства
По умолчанию в файлах конфигурации **Briseis** определены некоторые метрики для определенных устройств модельного ряда *D-Link*. Так, текущая конфигурация позволяет получить:

Описание | Имя метрики
:- | :-
Административно заданную скорость порта | CNS
Количество ошибок на интерфейсе | RX_crc
Cчетчик входящих бит | RX
Счетчик исходящих бит | TX
Статус дуплекса интерфейса | DS
Статус пары №1 | P1S
Статус пары №2 | P2S
Статус пары №2 для ревизии C1 | P2S/C1
Статус пары №3 для ревизии C1 | P3S/C1
Длину пары №1 | P1L
Длину пары №2 | P2L
Длину пары №2 для ревизии C1 | P2L/C1
Длину пары №3 для ревизии C1 | P3L/C1
Время работы устройства | UP
Версию программного обеспечения | FW

Модельный ряд *D-Link*: **DES-3200-28**, **DES-3200-18**, **DES-3200-28/C1**, **DES-3200-18/C1** и **DES-3028**.  
Если вы планируете использовать другое оборудование, оборудование других вендоров или же собирать иные метрики, то вам понадобится сконфигурировать программу, опираясь на приведенные примеры и описанные правила.

Структуры данные, которые я использую в файле конфигурации, может быть не очень удобно воспринимать, но зато они позволяют минимизировать число транзакций в сети и общее время опроса. На данный момент я опрашиваю около *3200* коммутаторов *D-Link*, в памяти формируется более *600 000* метрик, а сам сбор данных при этом занимает менее *1* минуты.



##Установка
+ Скопируйте файл **briseis** в '*/usr/local/etc/rc.d/*', а остальные файлы в '*/usr/local/etc/briseis/*'.  
+ Добавьте строку **briseis_enable="YES"** в файл '*/etc/rc.conf*'.
+ Запустите сервис командой **service briseis start**.