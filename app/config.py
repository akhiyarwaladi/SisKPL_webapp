
DEBUG = True
SECRET_KEY = 'something secret'

#REDIS_HOST = '192.168.0.10'
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379

BROKER_URL = 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT)

SOCKETIO_CHANNEL = 'tail-message'
MESSAGES_KEY = 'tail'
CHANNEL_NAME = 'tail-channel'

SOCKETIO_CHANNEL_2 = 'val-message'
MESSAGES_KEY_2 = 'val'
CHANNEL_NAME_2 = 'val-channel'
#DATATRAIN_decisionTree.pkl decTree_parameter.pkl
dataPath = "C:/data/lahan/input/"
modelPath = "C:/data/lahan/model/decTree_default.pkl"
shpPath = "C:/data/lahan/shp"
outputPath = "C:/data/lahan/hasil/"
finalOutputPath = "C:/data/lahan/hasil_akhir/"
gdbPath = "C:/data/lahan/data.gdb"
gdbPathDefault = "C:/Users/CI/Documents/ArcGIS/Default2.gdb"

ftpHost = "localhost"
ftpUser = "akhiyarwaladi"
ftpPaswd = "rickss12"


