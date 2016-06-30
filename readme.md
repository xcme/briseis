**Briseis** - многопроцессорный/многопоточный poller для Graphite, собирающий метрики с сетевых устройств по протоколу SNMPv2. Написан на Python и умеет работать как Unix-демон.

## Предназначение сервиса

Сервис был создан для обработки большого количества метрик в единицу времени. В большой сети общее количество метрик может составлять миллионы, поэтому их сбор и обработка занимает определенное время. С учетом накладных операций (сбор, подготовка и отправка данных и статистики) **Briseis** вполне справится с несколькими тысячами метрик в секунду.

Используя **Briseis** можно решать следующие задачи:

- Мониторить ошибки и загрузку на интерфейсах устройств
- Управлять конфигурацией устройств: сохранять, загружать, выгружать на внешний TFTP-сервер
- Получать прочие параметры, например загрузку CPU, температуру, состояния интерфейсов и т.д.

## Возможности Briseis

- Получение большого количества метрик за небольшой интервал времени
- Установка заранее определенных значений объектам SNMP (операция snmpset)
- Отправка произвольно выбранных метрик в Graphite (Carbon)

## Особенности

- Работа системным сервисом (daemon) под FreeBSD/Linux
- Гибкая система конфигурирования, возможность определять собственные метрики, группировать их, задавать их тип и способ опроса
- Отсутствие привязки к конкретному оборудованию или вендору
- Запуск нескольких дочерних процессов, каждый из которых может выполнять многопоточный опрос и собирать информацию с нескольких устройств одновременно
- Возможность упаковать несколько запросов в один для уменьшения общего количества транзакций
- Проверка устройств на доступность: опрос производится только для доступных в данный момент устройств
- Сортировка устройств в памяти по времени отклика: самые медленные устройства опрашиваются последними, самые быстрые - первыми
- Ведение статистики по доступности устройств и времени отклика
- Отправка данных на разные сервера Graphite, причем для каждого сервиса можно определить произвольный набор передаваемых метрик

## Требования

- Операционная система FreeBSD или Linux
- Python2 с модулям py-snmp и MySQLdb.
- Доступ к MySQL-серверу для получения списка устройств
- Доступ к MySQL-серверу для отправки статистики (опционально)

## Принцип работы

**Briseis** работает следующим образом:

1. Через определенный пользователем интервал обновляет из базы данных MySQL список устройств для опроса. Запрос в MySQL должен возвращать таблицу с полями '*id*', '*ip*', '*write_community*'.
2. Определяет модель для каждого устройства при помощи *snmpget* и пользовательского словаря.
3. Пытается проделать то же самое для устройств, которые не ответили при предыдущей попытке опроса.
4. Для каждого активного устройства выполняет набор операций *snmpset* или *snmpwalk* (последовательность зависит от настроек).
5. Для каждого активного устройства выполняет набор оставшихся операций (*snmpwalk* или *snmpset*, в зависимости от того, что опрашивалось первым).
6. Передает собранные метрики на сервера *Graphite (Carbon)*.
7. Отправляет в базу данных MySQL статистику последнего опроса.

Сам опрос реализован так:

- Опрос запускается в нескольких процессах. Каждый процесс порождает несколько потоков. Каждый из потоков последовательно опрашивает определенный список устройств. Все эти величины настраиваются.
- После каждого опроса **Briseis** запоминает для каждого устройства время, затраченное на получение всех данных.
- Перед каждым новым опросом устройства сортируются таким образом, чтобы самые быстрые из них опрашивались первыми.

В результате опроса в памяти оказывается несколько метрик. Их полные имена формируются из *префикса* (задается в свойствах каждого сервера), *IP-адреса* хоста, *имени группы метрик* (например, 'RX_crc') и *ключа*. Вместе эти параметры образуют полное имя метрики:
```
prefix.oct#1.oct#2.oct#3.oct#4.name.key
```

Помимо этого, каждая метрика имеет собственное *значение* и *временную метку*. На простом примере становится понятно, как вычисляются все упомянутые выше значения. Предположим, что у устройства с адресом '10.90.90.95' запрашивается  список ошибок на интерфейсах. Эта совокупность однородных метрик будет иметь одно общее имя, в нашем случае *RX_crc*. В конфигурационном модуля устройства это имя является ключом для опрашиваемого OID ('.1.3.6.1.2.1.16.1.1.1.8'). Упомянутый выше префикс задается в настройках для каждого сервера Graphite. Пусть он будет, к примеру, равен 'sw.'. Все эти параметры известны еще до опроса оборудования, а после опроса становятся известны и остальные. Так, индексы интерфейсов в нашем  случае будут представлять собой *key*, а полученные значения -  *value*. Время, когда **получена** метрика - это *timestamp* (пусть оно будет равным '1451595600').

Итак, при выполнения опроса по данному OID программа получит некоторый список:
```
.1.3.6.1.2.1.16.1.1.1.8.1  = Counter32: 84
.1.3.6.1.2.1.16.1.1.1.8.2  = Counter32: 0
...
.1.3.6.1.2.1.16.1.1.1.8.28 = Counter32: 0
```

Каждому интерфейсу (*key*) соответствует определенное значение счетчика (*value*). Если из конечного OID (он называется 'tag') вычесть OID, заданный в конфигурационном модуле, то получится этот самый *key*:

Описание         | Значение
---------------- | --------
Получили         | .1.3.6.1.2.1.16.1.1.1.8.28
Указано в модуле | .1.3.6.1.2.1.16.1.1.1.8
Разница (key)    | 28


Теперь можно получить полные имена метрик, их значения и временные метки:
```
sw.10.90.90.95.RX_crc.1 84 1451595600
sw.10.90.90.95.RX_crc.2  0 1451595600
...
sw.10.90.90.95.RX_crc.28 0 1451595600
```

Именно в таком виде метрики затем отправляются на сервера **Graphite**.

## Конфигурирование

### Описание параметров в файле bconfig.py

Параметр     | Описание
------------ | --------
snmp_wcomm   | SNMP write-community.
snmp_timeout | Таймаут ожидания ответа.
snmp_retries | Количество попыток получения ответа. Значение "1" означает, что будет предпринята 1 дополнительная попытка опроса, т.е. всего опросов будет 2.
no_retries   | Список команд snmpset, для которых параметр *retries* всегда будет равен 0. Ресурсозатратные операции имеет смысл помещать в этот список.


Параметр               | Описание
---------------------- | --------
max_processes          | Максимально возможное количество дочерних процессов.
max_devices_in_process | Максимальное количество устройств, обрабатываемых процессом. Если у вас 1000 устройств и вы планируете работу с двумя процессами, ставьте 500-600 (больше половины) - не ошибетесь.
max_threads            | Максимально возможное количество потоков.
max_requests_in_thread | Максимальное количество запросов в потоке. Под этим нужно понимать количество устройств, опрашиваемых одновременно.

С помощью этих параметров мы можем указать, что программе, к примеру, следует работать с **4** дочерними процессами, каждый из которых может запускать до **8** потоков, а каждый из этих потоков принимает на обработку до **12** устройств за раз. Манипуляция этими параметрами необходима если у вас большая сеть и при этом вы ходите собирать данные очень быстро. К примеру, хорошей практикой для отрисовки значений *RX/TX* является выбор интервала в *5* минут. Это значит, что программа должна полностью выполнить свою работу быстрее, чем за *5* минут. При этом мы столкнемся со следующими трудностями:

- Опрашивая устройства последовательно, мы будем тратить много времени на ожидание поступления данных по сети. Миллисекунды складываются в бесконечность. :)
- Запустив слишком много потоков одновременно мы можем полностью загрузить ядро процессора, увеличив тем самым время работы программы.
- Добавив еще процессов (по сути - ядер, т.к. новому процессу система может назначить другое ядро) можем резко увеличить число потоков и получить переполнение сокетов и ошибку вида "*kernel: sonewconn: pcb 0xfffff80075b06000: Listen queue overflow: 25 already in queue awaiting acceptance*" (для FreeBSD).

Наблюдая за работой программы можно подобрать оптимальные значения параметров чтобы не перегружать систему и в то же время быстро собирать данные.

Параметр                 | Описание
------------------------ | --------
logfile                  | Имя файла журнала.
query_interval           | Интервал, через который начинается новый цикл опроса (см. шаги выполнения программы).
sleep_interval           | Пауза между проверками текущего состояния. Поскольку проверка выполняется в бесконечном цикле, отсутствие паузы приведет к 100% загрузке CPU.
sleep_after_set_requests | Пауза, которую нужно выдержать после отправки **snmpset**-запросов. После такой команды устройство может быть занято ее выполнением, для этого и предусмотрена пауза перед дальнейшим опросом.
set_iter_delay           | Пауза, которая выдерживается после каждой операции **set**. Это позволяет использовать в одном проходе операции записи, требующие времени на выполнение (сохранение, выгрузка, загрузка конфигурации, например).
datasend_right_border    | Время в секундах, которое должно оставаться до истечения *query_interval*, чтобы началась передача данных в Graphite. Так, при *query_interval* в **300** секунд и *datasend_right_border* в **30** секунд, отправка данных начнется через **270** секунд после начала цикла опроса.
try_fix_query_errors     | Число попыток для перезапроса данных, если есть подозрение на ошибку в них. Ошибка, по-видимому, связана с самим Python и модулем net-snmp. В процессе написания программы после очередной оптимизации кода ошибки перестали появляться, но механизм их устранения остался.
try_fix_counters         | Флаг, указывающий на необходимость корректировки счетчиков, если их значения аномально высокие. Если установлен в *True*, то такие значения обнуляются. Это позволяет избежать пиков в петабайтах на графиках если счетчик был сброшен на самом устройстве в период опроса.
walk_before_set          | Флаг, определяющий порядок walk/set-операций. Если установлен в *True*, то операции **walk/get** выполняются первыми.

В некоторых случах работу программы требуется не ускорить, а, наоборот, замедлить. В основном это нужно для snmpset-операций. Дело в том, что такие операции вынуждают устройство предпринять какие то действия, которые требуют времени на выполнение. К примеру, если отправить на устройство команда для сохранения конфигурации, то она будет выполняться несколько секунд. В это время устройство может быть слишком загружено для того, чтобы выполнять другие команды. Другой пример - выгрузка конфигурации или лог-файлов на TFTP-сервер. В этом случае сервер может испытывать сильную нагрузку. Для ее снижения частоту выгрузки файлов нужно регулировать. Это регулирование возможно осуществить с помощью перечисленных выше таймаутов.

Параметр      | Описание
------------- | --------
mysql_addr    | Адрес MySQL-сервера, откуда будет забираться список устройств для опроса.
mysql_user    | Имя пользователя.
mysql_pass    | Пароль.
mysql_base    | Имя базы данных.
mysql_query_p | Запрос к базе данных для получения списка устройств. Запрос в MySQL должен возвращать таблицу вида '*id*', '*ip*', '*write_community*'.

Параметр        | Описание
--------------- | --------
useMySQLstat    | Параметр, определяющий будет ли использоваться запись статистики в MySQL. Может принимать значения *True* и *False*.
mysql_stat_addr | Адрес MySQL-сервера, куда будет сохраняться статистика.
mysql_stat_user | Имя пользователя.
mysql_stat_pass | Пароль.
mysql_stat_base | Имя базы данных.
mysql_stat_cset | Используемая кодировка.
mysql_stat_tabl | Имя таблицы статистики.

Параметр           | Описание
------------------ | --------
GraphiteCarbonList | Список серверов Graphite. Каждая запись в этом списке также представляет собой список, содержащий параметры сервера.

Пример записи:
```
[True, "graphite.localhost", 2003, "sw.", ['RX', 'TX', 'RX_crc', 'CT', 'CPU']]
```

№ параметра | Значение
----------- | --------
1           | Флаг использования конкретной записи. При *True* отправка данных на этот сервер выполняется, а при *False* нет.
2           | Адрес сервера Graphite, на который нужно отправлять метрики.
3           | Порт сервера.
4           | Префикс для имени метрики. На практике используется для того, чтобы размещать поступающие метрики в определенной директории.
5           | Список сокращенных имен метрик, которые должны быть переданы на сервер.

**Briseis** работает с серверами в том порядке, в каком они перечислены в параметре *GraphiteCarbonList*.


Параметр     | Описание
------------ | --------
default_info | Словарь параметров, которые запрашиваются у устройства первый раз. Эти параметры используются при классификации модели.

По умолчанию используется такое значение параметра *default_info*:
```
default_info = {
    'sys_descr'    : '.1.3.6.1.2.1.1.1.0',
    'sys_name'     : '.1.3.6.1.2.1.1.5.0',
    }
```

Параметр       | Описание
-------------- | --------
models_by_desc | Список соответствий описаний моделей устройств их именам. Само соответствие представлено в виде пары 'ключ' : 'значение'.

Пример параметра *models_by_desc*:
```
models_by_desc = [
    {'DES-3200-28/C1' : 'DES-3200-28_C1'},
    {'DES-3200-28'    : 'DES-3200-28'},
    {'DES-3200-18/C1' : 'DES-3200-18_C1'},
    {'DES-3200-18'    : 'DES-3200-18'},
    {'DES-3200-10'    : 'DES-3200-10'},
    {'DES-3028G'      : 'DES-3028G'},
    {'DES-3028'       : 'DES-3028'},
]
```
Когда **Briseis** получает с устройства параметры из *default_info*, то производится проверка на вхождение в эти параметры (*sys_descr* и *sys_name*) значений **ключей** словаря внутри списка *models_by_desc*. При **первом совпадении** именем модели считается соответствующее **значение** словаря. К примеру, *sys_descr* (.1.3.6.1.2.1.1.1.0) содержит значение **DES-3200-28/C1 Fast Ethernet Switch**. При переборе *models_by_desc* было установлено, что ключ **DES-3200-28/C1** входит в это значение. Таким образом, именем модели устройства будет значение **DES-3200-28_C1**. При этом классифицировать модели можно и по *sys_name*, т.е. имени, заданному пользователем.

Параметр    | Описание
----------- | --------
PassSetSet  | Набор метрик для **set**-операций, где ключом является порядковый номер текущей итерации опроса, а значением - список команд. 
PassSetWalk | Набор метрик для **walk**-операций, где ключом является порядковый номер текущей итерации опроса, а значением - список сокращенных имен метрик.

При каждой новой итерации программы производится поиск **максимального** значения ключа, **кратного** текущему **номеру** прохода. Затем для этого ключа определяется соответствующий набор метрик.

Примеры *PassSetSet* и *PassSetWalk*:
```
PassSet  = {
      1 : [],
     48 : ['SaveConf'],
     72 : ['UploadConf_3028'],
     96 : ['UploadConf_3200_C'],
    144 : ['UploadConf_3200_AB'],
    }

PassWalk = {
    1 : ['RX', 'TX', 'RX_crc', 'CT', 'CPU', 'CNS', 'DS', 'UP', 'FW'],
    2 : ['RX', 'TX', 'RX_crc', 'CT', 'CPU', 'CNS', 'DS', 'UP',     ],
    }
```

В данном примере для каждого 48-го цикла опроса выполняется сохранение конфигурации ("команда" 'SaveConf'). А каждый 2-й цикл метрика 'FW' не опрашивается.

Параметр | Описание
-------- | --------
oids_set | Набор метрик, соответствующих OID, ключей и значений для **set**-операций. Параметр '**oids_set**' представляет собой словарь, где ключи соответствуют имени модели, а значения содержат обрабатываемые объекты

Пример параметра *oids_set*:
```
{
'device_model1':{'query_name1':[ [tag1,iid1,val1,type1],[tag2,iid2,val2,type2],...,[tagN,iidN,valN,typeN] ],
                 'query_name1':[ [tag1,iid1,val1,type1],[tag2,iid2,val2,type2],...,[tagN,iidN,valN,typeN] ],},
'device_model2':{...}
}
```

**device_model** - имя словаря, содержащего списки объектов. Соответствует имени модели устройства.

**query_name** - имя списка объектов, обрабатываемых за один раз. Это означает, что **snmpset**-команды для всех перечисленных объектов будут отправлены одновременно в одном пакете **set-request**. Это может использоваться для экономии времени либо определяться требованиями оборудования для управления конкретными объектами.

**[tag,iid,val,type]** - список необходимых для snmpset параметров:

Параметр | Описание
-------- | --------
tag      | fully qualified, dotted-decimal, numeric OID
iid      | the dotted-decimal, instance identifier
val      | the SNMP data value
type     | SNMP data type

Пример: **['.1.3.6.1.2.1.17.7.1.4.3.1.2','777','\x00\x00\x00\xf0\x00\x00\x00\x00','OCTETSTR']**  
Эквивалентная команда: **snmpset -v2c -c private \<IP\> .1.3.6.1.2.1.17.7.1.4.3.1.2.777 x 000000f000000000**

Более полную информацию можно получить [здесь](https://net-snmp.svn.sourceforge.net/svnroot/net-snmp/trunk/net-snmp/python/README).

Таких списков внутри *query_name* может быть несколько.

Параметр  | Описание
--------- | --------
oids_walk | Набор метрик и соответствующих OID для **walk**-операций. Параметр '**oids_walk**' представляет собой "список, где ключи соответствуют имени модели, а значения содержат соответствие имен метрик и опрашиваемых OID.

Пример параметра *oids_walk*:
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

**device_model** - имя словаря, содержащего списки объектов. Соответствует имени модели устройства.

**metric_name** - краткое имя метрики.

**metric_oid** - OID, соответствующий краткому имени метрики.

**Важно:** Способ опроса устройства зависит от того, как задан параметр *metric_name*. Если в имени хотя бы одной из метрик словаря присутствует **точка**, то все OID упаковываются в **get-request**. В противном случае OID упаковываются в **walk-request**.

Предположим, что мы хотим получить значения *ifHCInOctets* (RX, 64 bit) с интерфейсов устройства. Мы можем описать пару метрика/OID как *Rx* = *{'~RX':'.1.3.6.1.2.1.31.1.1.1.6'}*. Поскольку точка в имени метрики '*~RX*' отсутствует, программа отправит **walk**-запрос и переберет указанный OID. Аналогично мы можем поступить и с *ifHCOutOctets* (TX, 64bit), описав еще одну пару *Tx* = *{'~TX':'.1.3.6.1.2.1.31.1.1.1.10',}*. При этом *Rx* и *Tx* представляют собой словари и, в свою очередь, являются ключом для *device_model*. Получается примерно такой список *oids_walk*:
```
oids_walk=[{
    'DES-3200-28':Rx,
},
    {
    'DES-3200-28':Tx,
}
]
```

Сначала программа выполняет **walk** для *Rx*, затем, перебирая список, делает то же самое для *Tx*. Обратите внимание на то, что мы используем имя устройства в каждом элементе списка только один раз. Попросту потому, что словарь не может содержать несколько одинаковых ключей. Если нам требуется задать для этого же типа устройств и другие значения, их следует помещать в другой элемент списка. Именно поэтому все словари *device_model* потом объединяются в список - чтобы для каждого типа устройств можно было выполнять несколько различных операций.

Теперь, когда мы окончательно запутались, приступим к разбору нюансов. :) Мы знаем, что **walk**-запрос по сути является последовательным перебором значений. Когда при переборе получено значение *tag*, выходящее за пределы заданного OID, перебор считается законченным. Каждый запрос - это сетевая транзакция, требующая некоторого времени. Чем больше транзакций в сети, тем больше мы ждем поступления данных и тем выше вероятность их случайных потерь. Поэтому мы можем пойти на хитрость - опрашивать *Rx* и *Tx* одновременно. Для этого создадим единый словарь *RxTx* = *{'~RX':'.1.3.6.1.2.1.31.1.1.1.6','~TX':'.1.3.6.1.2.1.31.1.1.1.10',}* и укажем его один раз:
```
oids_walk=[{
    'DES-3200-28':RxTx,
},
]
```

Теперь внутри **walk**-запроса мы будем перебирать сразу два адреса одновременно. При этом количество транзакций уменьшится вдвое. Единственное условие здесь - опрашиваемые ветки OID должны быть одинаковой длины (что очевидно при опросе таких значений как *Rx* и *Tx*, но вовсе не очевидно в других случаях), т.к. опрос будет прекращен при выходе за пределы одной из веток.

Но можно пойти и дальше. Мы можем переделать запрос как **get**, явно указав конкретные OID для конкретных интерфейсов. Теперь наш словарь будет выглядеть так:
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

Здесь мы задаем в качестве ключей словаря со списком метрик разные имена, но лишь потому, что не можем задать одно. Имя метрики в любом случае обрезается до точки, т.е. в итоге мы получаем либо '*RX*', либо '*TX*'. В полном имени метрики после краткого имени метрики будет добавлен ключ, как уже было рассказано выше.
Наш список будет выглядеть как и в предыдущем случае:
```
oids_walk=[{
    'DES-3200-28':RxTx,
},
]
```
Теперь наш запрос содержит все необходимые OID сразу. В итоге мы отправляем всего лишь один запрос и получаем всего лишь один ответ, в котором будут возвращены сразу 56 значений!  
**Важно**: В конечном итоге полные имена метрик никак не зависят от того, как именно мы формируем наши словари. Изменение словарей влияет на то, **что** именно мы собираем и **как** мы это делаем, а не на то, как имена метрик будут выглядеть после сбора данных.

## Модификаторы в именах метрик

Имена метрик могут содержать модификаторы, определяющие поведение программы по отношению к этим метрикам.

Модификатор | Описание
----------- | --------
**.**       | Меняет тип запроса с **walk** на **get**. При этом в полное имя метрики добавляется столько дополнительных чисел из OID, сколько точек содержится в кратком имени. К примеру, для OID '*.1.3.6.1.4.1.171.11.113.1.3.2.2.2.1.4.1.100*' и модификатора '..' ключом метрики будет уже не '*100*', а '*1.100*'.
**~**       | 64-битный счетчик. Выше в примерах мы использовали имена '*~RX*' и '*~TX*'. Такие метрики хранятся в памяти программы как служебные. Когда метрики будут опрошены второй раз, для каждой метрики будет посчитана разница между текущим и предыдущим значением. Так в памяти появятся еще две метрики, представляющие собой счетчики - '*RX*' и '*TX*'. Именно эти метрики и будут затем отправлены в **Graphite**.
**~~** | 32-битный счетчик. В остальном аналогичен 64-битному.

## Модули

Для удобства использования параметры *oids_set* и *oids_walk* описаны в **bconfig.py**, но вложенные в них объекты размещаются в отдельных модулях. Каждой модели устройства соответствует одноименный модуль, расположенный в директории */devices*. При запуске **Brises** загружает эти модули и формирует в памяти полную структуру *oids_set* и *oids_walk*.

Структура модулей точно такая же, как у [swtoolz-core](https://github.com/xcme/swtoolz-core). Внутри модулей находятся словари или списки. Пример словаря:
```
CPUutil = {
#    CPU           .1.3.6.1.4.1.171.12.1.1.6.3                          agentCPUutilizationIn5min
    'CPU.'      : '.1.3.6.1.4.1.171.12.1.1.6.3.0'
}
```
В этом словаре описана метрика для получения загрузки CPU устройства.

Пример списка:
```
CfgSave = [
#     .1.3.6.1.4.1.171.12.1.2.18.4                                      agentBscFileSystemSaveCfg
    ['.1.3.6.1.4.1.171.12.1.2.18.4', '0', '2', 'INTEGER'],
    ]
```
В этом списке описан набор параметров для snmpset, которые нужны для сохранения конфигурации устройства.

## Установка под FreeBSD
+ Скопируйте файл **briseis** в '*/usr/local/etc/rc.d/*', а остальные файлы в '*/usr/local/etc/briseis/*'.  
+ Добавьте строку **briseis_enable="YES"** в файл '*/etc/rc.conf*'.
+ Убедитесь, что firewall разрешает SNMP-запросы.
+ Запустите сервис командой **service briseis start**.

## Установка под Linux
+ Скопируйте файл **briseis** из директории '*linux*'  в '*/etc/init.d/*', а остальные файлы в '*/usr/local/etc/briseis/*'.
+ Убедитесь, что firewall разрешает SNMP-запросы.
+ Запустите сервис командой **service briseis start**.

## Список изменений

### [2.6.30] - 2016.06.30

#### Добавлено
- Возможность отсылать метрики строго в одни и те же интервалы времени
- Возможность корректировать счетчики при обработке, что позволяет избежать всплесков на графиках
- Возможность выполнять walk-опросы раньше, чем set
- Возможность отправлять метрики на несколько серверов Graphite
- Возможность выполнять некоторые запросы без повторных попыток

#### Изменено
- Модели теперь определяются так же, как и в [swtoolz-core](https://github.com/xcme/swtoolz-core)
- Конфигурация теперь размещается в отдельных модулях, как у [swtoolz-core](https://github.com/xcme/swtoolz-core)
- Изменен принцип выбора набора метрик для каждой итерации
- Описание было существенно переработано
- Исправлены некоторые некритичные ошибки

#### Удалено
- Отдельные настройки для Graphite
- Взаимодействие с [Attractor](https://github.com/xcme/attractor), т.к. с точки зрения программы этот сервис теперь не отличается от Graphite.
- Файл userdict.py

### [1.1.0] - 2015.07.11

#### Добавлено
- Добавлен параметр **set_iter_delay** для определения паузы между итерациями при выполнении **set**-операций
- Файл SQL для создания таблицы '**stats**'

#### Изменено
- Вместо процента недоступности устройства в таблицу статистики теперь записывается *число опросов* устройства
- Ключи словарей **oids_set** и **oids_walk** теперь сортируются в памяти
- Изменена документация в соответствии со сделанными изменениями

#### Удалено
- Файл changelog.txt

### [1.0.2] - 2015.03.18

#### Изменено
- Небольшие косметические изменения кода

#### Исправлено
- Исправлена ошибка, в результате которой в таблицу статистики могли попасть не все устройства

### [1.0.0] - 2015.03.05

Релиз версии 1.0.0
