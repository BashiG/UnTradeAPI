# *-* coding: utf-8 *-*

'''
Written by Konstantin Polyakov
Date: August, 2016

Thanks to authours of documentation:
-- embeddedpro.ucoz.ru
-- 2150692.ru/faq/47-at-komandy-sim900
-- 2150692.ru/faq/119-gsm-gprs-modul-aithinker-a6-bystryj-zapusk

'''

import os, serial, time

class SMS_PDU_Builder:
    def __init__(self):
        pass

    def _pack_message(message):
        return message

    def _build_absolute_time(self, datetime):
        pass

    def _build_relative_time(self, minutes):
        # vp = 0.. 143
        if minutes <= 60 * 12: vp = (minutes - 5) / 5                 # так как шаг 5 минут, то числа, не кратные 5, округляются в меньшую сторону.
        elif minutes <= 60 * 24: vp = (minutes-12+143*30)/30          # шаг в 30 минут
        elif minutes <= 60 * 24 * 30: vp = minutes/60/24 + 166        # шаг в 1 день
        elif minutes <= 60 * 24 * 7 * 63 : vp = minutes/60/24/7 + 192 # шаг в 1 день
        else: vp = 255

        if vp > 255: vp = 255

        return [int(vp)]


    def _build_address(self, address): # type(addres) = 'str'
        ''' Тип номера - 1 байт.
            7-й бит - всегда 1.
            6 ... 4-й бит - тип номера:
                000 - неизвестный
                001 - интернациональный
                010 - национальный
                011 - принятый в сети
                100 - тип подписчика в сети
                101 - алфавитноцифровой
                110 - сокращённый
                111 - зарезервирован
            3 ... 0-й бит - тип набора:
                0000 - неизвестный
                0001 - ISDN
                0010 - X.121
                0011 - телекс
                1000 - национальный
                1001 - частный
                1010 - ERMES
                1111 - зарезервирован
        '''
        type_of_number = 0x91 # интеенациональный
        # убираем '+'
        _sca = address if address[0] != '+' else address[1:]
        # определили длину (количество полуоктетов (полубайтов, тетрад))
        len_sca = len(_sca)
        # добавили 'F' в конец, если длина нечётная
        if (len_sca % 2 != 0): _sca += 'F'
        # переставляем тетрады местами
        sca = []
        for i in range(0, len(_sca), 2):
            sca.append(int(_sca[i+1] + _sca[i], 16))
        #print('-- SCA: ', sca)
        #print('-- SCA: ', sca2)

        return [len_sca, type_of_number] + sca

    def _build_tpdu(self, address, message, coding, delete_in_minutes): # delete_in_minutes = 1 день
        if (isinstance(delete_in_minutes, int)): VPF = '10'
        else: VPF = '11'
        PDU_type = [int(
            '0'  + # Reply Path - запрос ответа от стороны, прин6имающей сообщение
            '0'  + # UDHI - Определяет наличие заголовка в UD (данных пользователя).
                   #     0 - UD содержит только данные, 1 - UD содержит в добавление к данным и заголовок 
            '0'  + # Status Report Request - запрос на получение отчёта. SRR отличается от RP: SRR запрашивает отчёт от сервисного центра, а RP - от получаемой стороны
            VPF + # Validity Period Format - определяет формат поля VP
                   #     00 - поле VP отсутствует
                   #     01 - резерв в Siemens, расширенный формат для SonyErricson
                   #     10 - поле VP использут относительный формат
                   #     11 - поле VP использует абсолютный формат
            '0' +  # Reject Duplicates - говорит сервисному центру о необходимости удалять одинакове сообщения, если они ещё не переданы.
                   #     Одинаковыми считаются сообщения с совпадающими VR (Message Reference) и DA (Destination Address) и поступившие 
                   #     от одного OA (Originator Address)
                   #     0 - не удалять, 1 - удалять
            '01'   # Message Type Indicator.
                   #     Биты | телефон -> серв. центр  |  серв. центр -> телефон
                   #     ------------------------------------------------
                   #     00 - SMS-DELIVER REPORT SMS-DELIVER
                   #     01 - SMS-COMMAND   SMS-STATUS REPORT
                   #     10 - SMS-SUBMIT    SMS-SUBMIT REPORT
                   #     11 - RESERVED
            , 2)]

        # Количество успешно переданных - от 0x00 до 0xff. Устанавливается телефоном. Поэтому при передаче устанавливаем его в 0x00
        MR = [0x00]

        # Адрес приёмника сообщения (номер телефона получателя)
        DA = self._build_address(address)

        # Идентификатор протокола - указывает сервисному центру, как обработать передаваемое сообщение (факс, головосое сообщение и т. д.)
        PID = [0x00]

        # Схема кодирования данных в поле UD
        # Поле DCS представляет собой байт из двух тетрад по 4 бита.
        # Старшая тетрада (с 7 по 4) опаределяет группу кодирования,
        # а младшая ( с 3 по 0 ) - специфичекские данные для группы кодирования
        if coding == 'ascii': DCS = [0x00]
        elif coding == '8bit': DCS = [0x04]
        elif coding == 'ucs2': DCS = [0x08]
        '''DCS = [int(
            # 
            '00' +  #
            '' +  #
            '' +  #
            '' +  #
            '' +  #
            '' +  #
            ), 2]'''

        # время жизни сообщения
        if   VPF == '10': VP = self._build_relative_time(delete_in_minutes)
        elif VPF == '11': VP = self._build_absolute_time(delete_in_minutes)
        #if   ((PDU_type[0] && 0b00011000) >> 3) == 0b10: VP = self._build_relative_time(delete_in_minutes)
        #elif ((PDU_type[0] && 0b00011000) >> 3) == 0b11: VP = self._build_absolute_time(delete_in_minutes)

        # 140 байт данных пользователя (для ASCII (GSM) - это 160 символов, а для USC2 (unicode) - это 140 символов)
        if coding == 'ucs2': # unicode
            UD = list(bytearray(message, 'utf-16')) # с маркера (первых двух байт)
        elif coding == '8bit': # utf-8, без кириллицы
            UD = list(bytearray(message, 'utf-8')) # без маркера (первых двух байт)
        elif coding == 'ascii': # ascii "упаклванная" (сжатая)
            UD = self._pack_message(message)

        # Длина поля UD - подсчитываем не кол-во байт, а кол-во символолв.
        UDL = [len(UD)]

        #return PDU_type + MR + DA + PID + DCS + VP + UDL + UD
        #print(PDU_type, MR, DA, PID, DCS, VP, UDL, UD, sep=' -- ')
        return PDU_type + MR + DA + PID + DCS + VP + UDL + UD

    def build_pdu(self, address, message, sms_center_address='nothing', coding='ucs2', delete_in_minutes=1440):
        ''' Формат PDU осставлен из двух полей:
                - SCA (Service Centre Address)  - адрес сервисного центра рассылки коротких сообщений;
                - TPDU (Transport Protocol Data Unit) - пакет данных транспортного протокола.
            Некоторые модели мобильных телефонов и GSM-модемов не поддеррживают полный формат PDU
            и могут работать только с форматом TPDU. В этом случае SCA берётся из памяти SIM-карты,
            а поле SCA заменяется на 0x00.
        '''
        if sms_center_address == 'zero': sca = [0]
        elif sms_center_address == 'nothing': sca = []
        else: sca = self._build_address(sms_center_address)
        tpdu = self._build_tpdu(address, message, coding, delete_in_minutes)
        return bytes(sca), bytes(tpdu)

    def hex2hexString(self, HEX): # принимает байты. [0x0, 0xFF, 0x1A] -> '00FF1A'
        HEX = [str(hex(i))[2:] for i in HEX]
        return ''.join([i if len(i)%2==0  else '0'+i for i in HEX])


# Класс работы с GSM-модулем

class GSM:
    def __autoconnect(self):
        ports = os.listdir('/dev/')
        for port in ports:
            pattern = 'tty'#'ttyUSB'
            # не используем регулярные выражения ради скорости
            if len(port) <= len(pattern) or port[:len(pattern)] != pattern: continue
            try:
                print('Connected to /dev/'+port)
                return serial.Serial(port='/dev/'+port, baudrate=115200)
            except: 
                print(' ===== BAD ======')
        return False

    def __init__(self, port=None):
        if port is None:
            self.ser = self.__autoconnect()
            if self.ser == False:
                print('No serial ports to connect')
                exit()
        else: self.ser = serial.Serial(port=port, baudrate=115200)
        time.sleep(3)

        self.pdu_builder = SMS_PDU_Builder()

    def close(self): self.ser.close() 

    def read(self):
        r_text = bytes()
        while self.ser.inWaiting() > 0:
            r_text += self.ser.read(self.ser.inWaiting())

        if len(r_text) != 0:
            print('------ READED AS BYTES: ', r_text)
            print('------- READED AS LIST: ', list(r_text))
            print()

        return str(r_text, 'utf-8')

    def write(self, w_text, endline='\r', to_read=True):
        if isinstance(endline, str): endline = bytes(endline, 'utf-8')
        if isinstance(w_text, str): w_text = bytes(w_text, 'utf-8')
        w_text = w_text + endline

        print('------ WROTE AS BYTES: ', w_text)
        print('------- WROTE AS LIST: ', list(w_text))
        print()

        self.ser.write(w_text)
        time.sleep(0.5)

        if to_read: return self.read()

    def SMS_send(self, message, address, sets={}):
        if 'coding' not in sets:             sets['coding'] = 'ucs2'
        if 'delete_in_minutes' not in sets:  sets['delete_in_minutes'] = 10
        if 'sms_center_address' not in sets: sets['sms_center_address'] = 'zero'

        CONFIRM = bytes([26]) # (SUB) Ctrl-Z
        CANCEL  = bytes([27]) # ESC

        if self.SMS_mode == 'text':
            res = self.write('AT+CMGS="'+address+'"')
            self.write(bytes(message, 'utf-8'), endline=CONFIRM)

        elif self.SMS_mode == 'pdu':
            sca, tpdu = self.pdu_builder.build_pdu(address, message, sets['sms_center_address'], sets['coding'], sets['delete_in_minutes'])
            len_tpdu = str(len(tpdu))
            self.write('AT+CMGS='+len_tpdu)
            self.write(self.pdu_builder.hex2hexString(sca + tpdu), endline=CONFIRM)

    def SMS_read(self):
        r_text = bytes()
        while self.ser.inWaiting() > 0:
            r_text += self.ser.read(1)
        return r_text

    def SMS_setMode(self, mode):
        if mode == 'pdu':
            ser.write('AT+CMGF=0')
        elif mode == 'text':
            ser.write('AT+CMGF=1')
        self.SMS_mode = mode

if __name__ == '__main__':

  # Тест GSM

  ser = GSM()
  try:
  	# отключает или включает эхо
    #ser.write('ATE0')
    ser.write('AT')#'AT+CUSD=1,"*100#",15\r\n')
    #ser.write('ATI')
    # получаем нолмер сервисного центра
    #ser.write('AT+CSCA?')
    # кодировка текстового режима. Доступны: GSM, UCS2, HEX
    #ser.write('AT+CSCS="GSM"')

    #print(ser.write('ATV1')) # отключаем эхо команд

    address = '+79998887766'

    ser.SMS_setMode('pdu')    
    ser.SMS_send('  Latinica Кирилица Ё', address)
    time.sleep(5)
    ser.SMS_setMode('text')    
    ser.SMS_send('  Latinica Кирилица Ё', address)

    while 1:
      w_text = input()
      if w_text == 'exit': break
      if w_text != '': ser.write(w_text)
      r_text = ser.read()

    print('\n\n---------------\nSTOPPED')
  finally:
    ser.close()
