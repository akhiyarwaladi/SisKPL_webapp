import time
from datetime import datetime
from celery import Celery
from flask import Flask, render_template, request, flash
from redis import StrictRedis
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from celery.task.control import revoke
import urllib2
from assets import assets
import config
import celeryconfig
import os
from sklearn.externals import joblib


import arcpy
from arcpy.sa import *
import pandas as pd
import numpy as np
import os.path
import ftpClient as ft
import shutil
import gc

redis = StrictRedis(host=config.REDIS_HOST)
redis.delete(config.MESSAGES_KEY)
redis.delete(config.MESSAGES_KEY_2)
# celery = Celery(__name__)
# celery.config_from_object(celeryconfig)

app = Flask(__name__)
app.config.from_object(config)
assets.init_app(app)

app.config['SECRET_KEY'] = 'top-secret!'
app.config['SOCKETIO_CHANNEL'] = 'tail-message'
app.config['MESSAGES_KEY'] = 'tail'
app.config['CHANNEL_NAME'] = 'tail-channel'

app.config['SOCKETIO_CHANNEL_2'] = 'val-message'
app.config['MESSAGES_KEY_2'] = 'val'
app.config['CHANNEL_NAME_2'] = 'val-channel'

app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

#Folder content deleter
def folder_content_deleter(folder_path):
    for the_file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            pass

#gdb content deleter
def gdb_content_deleter(wrkspc):
    for r,d,fls in arcpy.da.Walk(wrkspc, datatype=['FeatureClass','FeatureDataset','Geo', 'RasterDataset']):
        for f in fls:
            print f
            try:
                arcpy.Delete_management(os.path.join(r,f))
            except:
                pass
                
def internet_on():
    for timeout in [1,5,10,15]:
        try:
            response=urllib2.urlopen('http://google.com',timeout=timeout)
            return True
        except urllib2.URLError as err: pass
    return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if(internet_on()):
            if redis.llen(config.MESSAGES_KEY):
                flash('Task is already running', 'error')
            # elif(redis.llen(config.MESSAGES_KEY) == 0):
            #     flash('Task is finished', 'success')
            else:
                tail.delay()
                flash('Task started. Please wait until complete', 'info')
        else:
            flash('Internet connection is bad. Please pay your internet bill :)','error')

    return render_template('index.html')

@app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    socketio_manage(request.environ, {
        '/tail': TailNamespace
    })
    return app.response_class()

@app.route('/stop', methods=['GET', 'POST'])
def stop():
    if request.method == 'POST':
        tail.delay()
    return render_template('index.html')

def clear_all():
    """Clears all the variables from the workspace of the spyder application."""
    gl = locals().copy()
    for var in gl:
        if var[0] == '_': continue
        if 'func' in str(locals()[var]): continue
        if 'module' in str(locals()[var]): continue

        del locals()[var]

@celery.task
def tail():

    while(1):
        # buka file csv untuk mengetahui scene yang telah selesai diproses
        log = pd.read_csv("logComplete.csv")
        liScene = log["scene"].tolist()
        liDate = log["dateComplete"].tolist()

        msg = str(datetime.now()) + '\t' + "Importing Library ... \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        
        arcpy.CheckOutExtension("spatial")
        # pass list yang telah selesai ke ftp download
        filenameNow, scene, boolScene, year, month = ft.downloadFile(liScene)

        if(boolScene == False):
            print "Data hari ini selesai diproses"
            time.sleep(1000)

        #definisikan nama file yang akan diproses
        filename = filenameNow
        # definisikan nama file keluaran hasil klasifikasi yang masih mentah
        filenameOut = filenameNow + "_classified.TIF"
        # definisikan letak file ers yang telah didownload dalam workstation
        dataPath =  config.dataPath + scene + "/" + filename
        # definisikan letak model .pkl hasil training data sampel
        modelPath = config.modelPath
        # definisikan shp file indonesia untuk cropping batas administrasi
        shpPath = config.shpPath

        # definisikan folder keluaran hasil proses
        outFolder = config.outputPath + filename.split(".")[0]
        # jika folder ada maka hapus 
        if(os.path.exists(outFolder)):
            shutil.rmtree(outFolder)
        # buat folder yang telah didefinisikan
        os.makedirs(outFolder)
        # definisikan path file keluaran
        outputPath = outFolder + "/" + filenameOut

        ##################### KONVERSI DATA ERS KE TIAP BAND ######################################
        print ("converting b3")
        if(os.path.exists(dataPath + "TOA_B3" + ".TIF")):
            os.remove(dataPath + "TOA_B3" + ".TIF")
        # Ambil hanya band 3 dan jadikan raster
        try:
            b_green = arcpy.Raster( dataPath  + "/B3" ) * 1.0
        except :
            b_green = arcpy.Raster( dataPath  + "/Band_3" ) * 1.0
        
        print ("saving b3")
        msg = str(datetime.now()) + '\t' + "saving b3 \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        # save raster band 3 ke folder data input
        b_green.save(dataPath + "TOA_B3" + ".TIF" )
        del b_green

        print ("converting b5")
        if(os.path.exists(dataPath + "TOA_B5" + ".TIF")):
            os.remove(dataPath + "TOA_B5" + ".TIF")
        # Ambil hanya band 5 dan jadikan raster
        try:
            b_nir = arcpy.Raster( dataPath  + "/B5" ) * 1.0
        except:
            b_nir = arcpy.Raster( dataPath  + "/Band_5" ) * 1.0
        
        print ("saving b5")
        msg = str(datetime.now()) + '\t' + "saving b5 \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        # save raster band 5 ke folder data input
        b_nir.save( dataPath +  "TOA_B5" + ".TIF" )
        del b_nir

        print ("converting b6")
        if(os.path.exists(dataPath + "TOA_B6" + ".TIF")):
           os.remove(dataPath + "TOA_B6" + ".TIF")
        # Ambil hanya band 6 dan jadikan raster
        try:
            b_swir1 = arcpy.Raster( dataPath + "/B6") * 1.0
        except Exception as e:
            b_swir1 = arcpy.Raster( dataPath + "/Band_6") * 1.0

        msg = str(datetime.now()) + '\t' + "saving b6 \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        print ("saving b6")
        # save raster band 6 ke folder data input
        b_swir1.save( dataPath + "TOA_B6" + ".TIF" )
        del b_swir1

        ####################### SELESAI KONVERSI DATA #######################################
        
        #################### UBAH RASTER KE FORMAT DATAFRAME ###############################
        msg = str(datetime.now()) + '\t' + "Processing file "+filename+"\n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        # load semua raster yang telah dikonversi diawal
        rasterarrayband6 = arcpy.RasterToNumPyArray(dataPath + "TOA_B3.TIF")
        rasterarrayband5 = arcpy.RasterToNumPyArray(dataPath + "TOA_B5.TIF")
        rasterarrayband3 = arcpy.RasterToNumPyArray(dataPath + "TOA_B6.TIF")
        
        print("Change raster format to numpy array")
        # gabungkan 3 array data secara horizontal
        data = np.array([rasterarrayband6.ravel(), rasterarrayband5.ravel(), rasterarrayband3.ravel()], dtype=np.int16)
        # ubah menjadi vertikal untuk kebutuhan prediksi .pkl
        data = data.transpose()

        # langsung hapus variabel yang tidak digunakan lagi
        del rasterarrayband5
        del rasterarrayband3

        print("Change to dataframe format")
        msg = str(datetime.now()) + '\t' + "Change to dataframe format \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        #time.sleep(1)

        # definisikan nama kolom dataframe
        columns = ['band3','band5', 'band6']
        # ubah array vertical menjadi dataframe
        df = pd.DataFrame(data, columns=columns)
        # hapus array vertikal
        del data
        ###################### SELESAI ####################################################
        print("Split data to 20 chunks ")
        msg = str(datetime.now()) + '\t' + "Split data to 20 chunks \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)
        #time.sleep(1)

        # bagi data menjadi 20 bagian karena program tidak kuat prediksi sekaligus
        df_arr = np.array_split(df, 20)
        # hapus dataframe
        del df
        # load classifier (model pkl) yang telah di train
        clf = joblib.load(modelPath) 

        # definisikan array untuk menampung nilai integer hasil prediksi
        kelasAll = []
        # ulangi untuk setiap bagian data
        for i in range(len(df_arr)):
            
            print ("predicting data chunk-%s\n" % i)
            msg = str(datetime.now()) + '\t' + "predicting data chunk-%s\n" % i
            redis.rpush(config.MESSAGES_KEY, msg)
            redis.publish(config.CHANNEL_NAME, msg)

            msg2 = i
            redis.rpush(config.MESSAGES_KEY_2, msg2)
            redis.publish(config.CHANNEL_NAME_2, msg2)
            #time.sleep(1)
            # fungi untuk prediksi data baru dengan data ke i
            kelas = clf.predict(df_arr[i])

            # buat dataframe kosong
            dat = pd.DataFrame()
            # masukkan hasil prediksi data ke i ke kolom kelas
            dat['kel'] = kelas
            print ("mapping to integer class")
            msg = str(datetime.now()) + '\t' + "mapping to integer class \n"
            redis.rpush(config.MESSAGES_KEY, msg)
            redis.publish(config.CHANNEL_NAME, msg)
            #time.sleep(1)
            # definisikan dictionary untuk ubah string kelas ke integer kelas prediksi
            mymap = {'awan':1, 'air':2, 'tanah':3, 'vegetasi':4}
            # fungsi map dengan parameter dictionary
            dat['kel'] = dat['kel'].map(mymap)

            # ubah kolom dataframe ke array 
            band1Array = dat['kel'].values
            # ubah array ke numpy array dengan tipe unsigned 8 untuk menghindari memory error
            band1Array = np.array(band1Array, dtype = np.uint8)
            print ("extend to list")
            msg = str(datetime.now()) + '\t' + "extend to list \n"
            redis.rpush(config.MESSAGES_KEY, msg)
            redis.publish(config.CHANNEL_NAME, msg)
            #time.sleep(1)
            #kelasAllZeros[] = band1Array
            # masukkan numpy aray ke list prediksi
            kelasAll.extend(band1Array.tolist())
            # mencoba cek array hasil prediksi
            print(kelasAll[1:10])
            
        # hapus semua variabel yang tidak digunakan lagi
        del df_arr
        del clf
        del kelas
        del dat
        del band1Array

        print ("change list to np array")
        msg = str(datetime.now()) + '\t' + "change list to np array \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        # ubah list prediksi ke numpy array
        kelasAllArray = np.array(kelasAll, dtype=np.uint8)
        # hapus list prediksi
        del kelasAll
        print ("reshaping np array")
        msg = str(datetime.now()) + '\t' + "reshaping np array \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        # reshape numpy array 1 dimensi ke dua dimensi sesuai format raster
        band1 = np.reshape(kelasAllArray, (-1, rasterarrayband6[0].size))
        # ubah tipe data ke unsigned integer
        band1 = band1.astype(np.uint8)

        # load raster band6 untuk kebutuhan projeksi dan batas batas raster
        raster = arcpy.Raster(dataPath + "TOA_B6.TIF")
        inputRaster = dataPath + "TOA_B6.TIF"

        # ambil referensi spatial
        spatialref = arcpy.Describe(inputRaster).spatialReference
        # ambil tinggi dan lebar raster
        cellsize1  = raster.meanCellHeight
        cellsize2  = raster.meanCellWidth
        # definisikan extent dari raster dan point dari extent
        extent     = arcpy.Describe(inputRaster).Extent
        pnt        = arcpy.Point(extent.XMin,extent.YMin)

        # hapus yang tidak dipakai lagi
        del raster
        del rasterarrayband6
        del kelasAllArray

        # save the raster
        print ("numpy array to raster ..")
        msg = str(datetime.now()) + '\t' + "numpy array to raster .. \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        # ubah numpy array ke raster dengan atribut yang telah didefinisikan
        out_ras = arcpy.NumPyArrayToRaster(band1, pnt, cellsize1, cellsize2)

        arcpy.CheckOutExtension("Spatial")
        print ("define projection ..")
        msg = str(datetime.now()) + '\t' + "define projection ..\n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        # simpan raster hasil konversi ke path yang telah didefinisikan
        arcpy.CopyRaster_management(out_ras, outputPath)
        # definisikan projeksi dengan referensi spatial
        arcpy.DefineProjection_management(outputPath, spatialref)
        # hapus yang tidak digunakan lagi
        del out_ras
        del band1
        del spatialref
        del cellsize1
        del cellsize2
        del extent
        del pnt
        ########################### MASKING CLOUD AND BORDER #########################
        print("Masking Cloud")
        # load file cm hasil download yang disediakan
        mask = Raster(os.path.dirname(dataPath) + "/" + filename.split(".")[0] + "_cm.ers")
        # load raster hasil klasifikasi mentah 
        inRas = Raster(outputPath)
        # jika file cm bernilai 1 = cloud, 2 = shadow, 11 = border
        # ubah nilai tersebut menjadi 1 dan lainnya menjadi 0
        inRas_mask = Con((mask == 1), 1, Con((mask == 2), 1, Con((mask == 11), 1, 0)))
        #inRas_mask = Con((mask == 1), 1, Con((mask == 2), 1, Con((mask == 11), 1, Con((mask == 3), 1, Con((mask == 4), 1, Con((mask == 5), 1, Con((mask == 6), 1, Con((mask == 7), 1, 0))))))))

        # buat raster yang merupakan nilai no data dari hasil kondisi diatas, hasilnya nodata = 1
        # saya juga tidak mengerti yang bukan cloud jadi no data
        mask2 = IsNull(inRas_mask)
        # jika raster bernilai 1 maka ubah jadi 0, jika tidak tetap nilai raster hasil kondisi
        inRas2 = Con((mask2 == 1), 0, inRas_mask)
        # simpan raster pure dimana semua nilai 1 akan dihilangkan dari hasil klasifikasi
        inRas2.save(os.path.dirname(outputPath) + "/" + filenameOut.split(".")[0] + "_mask.TIF")
        # jika raster bernilai 1 maka jadi no data, jika tidak maka tetap si raster hasil awal
        inRas_mask2 = SetNull(inRas2 == 1, inRas)
        # simpan raster yang telah bersih dari cloud dan border yang jelek
        inRas_mask2.save(os.path.dirname(outputPath) + "/" + filenameOut.split(".")[0] + "_maskCloud.TIF")

        # hapus variabel conditional yang tidak digunakan lagi
        del mask
        del mask2
        del inRas
        del inRas2
        del inRas_mask
        del inRas_mask2
        ############################## SELESAI ###########################################

        ####################### MASKING DENGAN SHP INDONESIA ##############################
        print("Masking with shp indonesia")
        arcpy.CheckOutExtension("Spatial")
        # buka file shp indonesia
        inMaskData = os.path.join(shpPath, "INDONESIA_PROP.shp")
        # buka raster hasil masking cloud dan border
        inRasData = Raster(os.path.dirname(outputPath) + "/" + filenameOut.split(".")[0] + "_maskCloud.TIF")
        # terapkan fungsi masking dengan shapefile
        try:
            outExtractByMask = ExtractByMask(inRasData, inMaskData)
            print("Saving in: " + str(os.path.dirname(outputPath) + "/" + filenameOut.split(".")[0] + "_maskShp.TIF"))
            # simpan hasil masking
            
            outExtractByMask.save(os.path.dirname(outputPath) + "/" + filenameOut.split(".")[0] + "_maskShp.TIF")
            # hapus lagi dan lagi variabel yang tidak digunakan
            del inMaskData
            del inRasData
            del outExtractByMask        
        except:
            print "diluar indonesia shp"
            pass
        
        ########################## SELESAI ################################################

        arcpy.Delete_management("in_memory")

        ####################### SAVE LOG DATA YANG TELAH SELESAI DIPROSES ########################################
        liScene.append(scene)
        liDate.append(str(datetime.now()))

        print(liScene)
        print(liDate)

        serScene = pd.Series(liScene)
        serDate = pd.Series(liDate)

        print(serScene)
        print(serDate)
        log2 = pd.DataFrame()
        log2["scene"] = serScene
        log2["dateComplete"] = serDate

        print(log2.head(5))
        log2.to_csv("logComplete.csv", index=False)

        del liScene
        del liDate
        del serScene
        del serDate
        del log
        del log2
        ##########################################################################################################
        # delete downloaded data in workstation
        shutil.rmtree(os.path.dirname(dataPath))
        #shutil.rmtree(outFolder)
        print ("Finished ..")
        msg = str(datetime.now()) + '\t' + "Finished ... \n"
        redis.rpush(config.MESSAGES_KEY, msg)
        redis.publish(config.CHANNEL_NAME, msg)

        redis.delete(config.MESSAGES_KEY)
        redis.delete(config.MESSAGES_KEY_2)

        # local variable to list
        dictLocal = locals()
        # delete all local variable, hope will free some space
        for key in dictLocal.keys():
            del key
        clear_all()
        print "local var: " + str(locals())
        gc.collect()


class TailNamespace(BaseNamespace):
    def listener(self):
        # Emit the backlog of messages
        messages = redis.lrange(config.MESSAGES_KEY, 0, -1)        
        messages2 = redis.lrange(config.MESSAGES_KEY_2, 0, -1)

        print(messages2)
        self.emit(config.SOCKETIO_CHANNEL, ''.join(messages))
        self.emit(config.SOCKETIO_CHANNEL_2, ''.join(messages2))

        self.pubsub.subscribe(config.CHANNEL_NAME)
        self.pubsub.subscribe(config.CHANNEL_NAME_2)
        i=8
        for m in self.pubsub.listen():
            if m['type'] == 'message':
                self.emit(config.SOCKETIO_CHANNEL, m['data'])
                self.emit(config.SOCKETIO_CHANNEL_2, i)
                i=i+1

    def on_subscribe(self):
        self.pubsub = redis.pubsub()
        self.spawn(self.listener)
