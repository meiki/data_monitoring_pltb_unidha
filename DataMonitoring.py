from gpiozero import Button as Terang
import random
import time
import RPi.GPIO as GPIO
import lcddriver
import requests
import json
from datetime import datetime
from ina219 import INA219, DeviceRangeError
from time import sleep
import os




#-------------------------------------- Sensor Current Voltage
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 2.0
ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
ina.configure(ina.RANGE_16V)

#------------------------------------- Sensor Anemometer & Rpm Poros
#KONSTANTA
PI = 3.141
RHO = 1.18 #kg/m3
PERIODE = 10
DELAYTIME= 10
RADIUS = 100
RADIUS_POROS = 100 #milik poros turbin
JML_CELAH_ANEMO = 18
JML_CELAH_POROS = 18 #milik poros turbin
TUNDA = 7

#VARIABEL
sample = 0
hitung_celah_anemo = 0
hitung_celah_poros = 0 
rpm_anemo = 0.00
rpm_poros = 0.00
rpm_generator = 0.00
kecepatanGenerator = 0.00
kecepatanAngin = 0.00

luas_penampang = 2.4
anemoOffset = 0.2

voltase = 0.00
arus = 0.00
daya_generator = 0.00
efisiensi = 0.00

#SETUP
celahAnemo = Terang(17) # gpio no.11
celahPoros = Terang(13) #milik poros turbin | gpio no.13

file_path = 'data_sementara.txt'
urlSendData = "http://DomainAnda.com/api/data"
urlCheckConnection = "http://DomainAnda.com"
timeout = 5

#MENGUKUR

def mengukur():
    global hitung_celah_poros
    global hitung_celah_anemo
    global voltaseCounter
    global voltaseValue
    global voltaseTotal
    global arusCounter
    global arusValue
    global arusTotal
    
    voltaseCounter = 0
    voltaseTotal = 0.00
    voltaseValue = 0.00
    
    arusCounter = 0
    arusValue = 0.00
    arusTotal = 0.00
    
    hitung_celah_poros = 0
    hitung_celah_anemo = 0
    start = time.time()
    while(time.time() < start + PERIODE):
        celahPoros.when_pressed = hitungCelahPoros
        celahAnemo.when_pressed = hitungCelahAnemo
    hitungData()
    
def hitungCelahAnemo():
    global hitung_celah_anemo
    hitung_celah_anemo += 1
    
def hitungCelahPoros():
    global hitung_celah_poros
    global voltaseCounter
    global voltaseValue
    global voltaseTotal
    global arusCounter
    global arusTotal
    global arusValue
    
    voltaseValue = ina.shunt_voltage()*10
    arusValue = ina.current()/1000
    voltaseTotal = voltaseTotal + voltaseValue   
    arusTotal = arusTotal + arusValue
    
    hitung_celah_poros += 1
    voltaseCounter += 1
    arusCounter += 1
    
def hitungData():
    global rpm_anemo
    global rpm_poros
    global kecepatanGenerator
    global kecepatanAngin
    global angin_pangkat
    global voltase
    global arus
    global daya_angin
    global daya_generator
    global efisiensi
    
    print('------------------------------------------------------')
    print("Jumlah Celah Anemo   : ", hitung_celah_anemo)
    print("Jumlah Celah Poros   : ", hitung_celah_poros)
    
    rpm_anemo = ((hitung_celah_anemo/JML_CELAH_ANEMO)*60)/(PERIODE); # Menghitung Putaran Per Menit (RPM)
    print("RPM Anemometer  : %.0f" % rpm_anemo + " rad/s")
    
    rpm_poros = ((hitung_celah_poros/JML_CELAH_POROS )*60)/(PERIODE); # Menghitung RPM POROS
    print("RPM Poros       : %.0f" % rpm_poros + " rad/s")
    
    rpm_generator = ((hitung_celah_poros/JML_CELAH_POROS )*60)/(PERIODE);
    print("RPM Generator   : %.0f" % rpm_generator + " rad/s ")
    
    kecepatanGenerator = (((3.8 * PI * RADIUS_POROS * rpm_generator)/60)/1000);
    print("Kecepatan Generator : %.2f" % kecepatanGenerator)
    
    if (rpm_anemo <= 0.00):
        kecepatanAngin = 0
    else:
        kecepatanAngin = (((2 * PI * RADIUS * rpm_anemo)/60)/1000)+anemoOffset; # Hitung Kecepatan Angin pada m/s
    
    print("Kecepatan Angin     : %.2f" % kecepatanAngin + " m/s")
    
    if (rpm_poros <= 0.00):
        voltase = 0.00
        arus = 0.00
        daya_generator = 0.00
        efisiensi = 0.00
        daya_angin = 0.00
    else:
        voltase = voltaseTotal/voltaseCounter
        arus = arusTotal/arusCounter
        daya_generator = voltase*arus
        angin_pangkat = (kecepatanAngin*kecepatanAngin*kecepatanAngin)
        daya_angin = (1.2*angin_pangkat*1.18)/2
        
        if(daya_angin > 0.00):
            efisiensi = (daya_generator/daya_angin)*100 
            efisiensi = 0
    print("Voltase Counter  : ", voltaseCounter)
    print("Voltase   : " + str("%.2f" % voltase) + "V")
    print("Arus Counter  : ", arusCounter)
    print("Arus    : " + str("%.2f" % arus) + "A")
    print("Daya Generator: " + str("%.2f" % daya_generator) + " Watt")
    print("Daya Angin: " + str("%.2f" % daya_angin) + " Watt")
    print("Efisiensi : " + str("%.0f" % efisiensi) + "%")
        
def simpanData():
    
    #------------------------data yang dikirim ke server--------------------------------
    dataTurbin = {"kecepatan_angin": kecepatanAngin,
         "voltase": voltase,
         "arus": arus,
         "putaran_poros":rpm_poros,
         "daya":daya_generator,
         "efisiensi": efisiensi,
         "created_at": dtstring,
         "updated_at": dtstring
         }
    is_web_connected = cekWebConnection()
    if is_web_connected:
        is_data_sementara = cekDataSementara()
        
        if is_data_sementara:  
            kirimDataSementara()
        
        sendDataToServer(dataTurbin)
    else:
        simpanDataSementara(dataTurbin)

def kirimDataSementara():
    
    file = open(file_path,"r")
    lines = file.readlines()
    file.close()
    
    
    print("-- Baca Data sementara  untuk Dikirim : ---")
    count = 0
    for line in lines:
        count += 1 
        data = line.strip("\n")
        print("No.", count )
        print(data)
        newfile = open(file_path,"w")
        is_data_sementara_send = sendDataSementaraToServer(eval(data))
        if is_data_sementara_send:
            if line.strip("\n") != data:
                newfile.write(line)
                print("---- NewDataSementara ---")
                print(line)
        newfile.close()
    print("---------------------")
    

def sendDataSementaraToServer(data):
    try:
        response = requests.post(urlSendData, data=data)
        if (response.ok):
            print("Data Sementara Berhasil Dikirim !, Status Code: ", response.status_code)
            print(data)
            print("---------------------")
            return True
        else:
            print("Data Smentara Gagal Dikirim ! Status Code: ", response.status_code)
            print(data)
            print("---------------------")
            print("----- Simpan Data Sementara -----")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print("Data Sementara Gagal Dikirim ! Connection Error...! ")
        print(e)
        print("----- Simpan Data Sementara -----")
        return False
        
def sendDataToServer(data):
    try:
        response = requests.post(urlSendData, data=data)

        if (response.ok):
            print("Data Berhasil Dikirim !, Status Code: ", response.status_code)
            print(data)
            print("---------------------")
        else:
            print("Data Gagal Dikirim ! Status Code: ", response.status_code)
            print(data)
            print("---------------------")
            print("----- Simpan Data Sementara -----")
            simpanDataSementara(data)
            
    except requests.exceptions.ConnectionError as e:
        print("Data Gagal Dikirim ! Connection Error...! ")
        print(e)
        print("----- Simpan Data Sementara -----")
        simpanDataSementara(data)
    
def cekDataSementara():
    is_empty = is_file_empty(file_path)
    if is_empty:
        print("File Data Sementara is Empty ..!")
        return False
    else:
        print("File Data Sementara is not empty ... !")
        bacaDataSementara()
        return True
        
def cekWebConnection():
    try:
        request = requests.get(urlCheckConnection, timeout=timeout)
        print("connected to web server")
        return True
    except (requests.ConnectionError, requests.Timeout) as e:
        print("Not Connected to web server.. !", e)
        return False
    
def is_file_empty(file_path):
    return os.path.exists(file_path) and os.stat(file_path).st_size == 0
    

def simpanDataSementara(data):
    file = open(file_path , "a")
    file.write(str(data)+"\n")
    file.close()
    print("-- Data Berhasil Disimpan ! -----")
    bacaDataSementara()

def bacaDataSementara():
    file = open(file_path,"r")
    lines = file.readlines()
    print("-- Data sementara tersimpan : ---")
    count = 0
    for line in lines:
        data = line
        print(data)
    print("---------------------")
    file.close()
        
# port init
def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    # set up the SPI interface pins
    GPIO.setup(SPIMOSI, GPIO.OUT)
    GPIO.setup(SPIMISO, GPIO.IN)
    GPIO.setup(SPICLK, GPIO.OUT)
    GPIO.setup(SPICS, GPIO.OUT)
    pass
    
# read SPI data from MCP3008(or MCP3204) chip,8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 7) or (adcnum < 0)):
        return -1
    GPIO.output(cspin, True)

    GPIO.output(clockpin, False)  # start clock low
    GPIO.output(cspin, False)  # bring CS low

    commandout = adcnum
    commandout |= 0x18  # start bit + single-ended bit
    commandout <<= 3  # we only need to send 5 bits here
    for i in range(5):
        if (commandout & 0x80):
            GPIO.output(mosipin, True)
        else:
            GPIO.output(mosipin, False)
        commandout <<= 1
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        
    adcout = 0
    # read in one empty bit, one null bit and 10 ADC bits
    for i in range(12):
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        adcout <<= 1
        if (GPIO.input(misopin)):
            adcout |= 0x1

    GPIO.output(cspin, True)

    adcout >>= 1  # first bit is 'null' so drop it
    return adcout
    

while True:
    now = datetime.now()
    dtstring = now.strftime ("%Y-%m-%d %H:%M:%S")
    sample += 1
    
    print("-------------------------------")
    print(sample)
    print("tanggal: ", dtstring)
    print("Mulai Mengukur...")
    
    mengukur()
    
    print("Selesai...... !")
    print("")
    print('------------------------------------------------------')
    
    print("Mulai mengirim data ke server..... !")
    simpanData()
    
    time.sleep(TUNDA)                   
    

