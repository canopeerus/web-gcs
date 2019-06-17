import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb
sb.set()

#read csv file, rename columns, and drop 2nd row as it has indexes also.
def convert_time(s):
    h, m, s = map(int, s.split(':'))
    return pd.datetools.timedelta(hours=h, minutes=m, seconds=s)


params_list = ['Date','time','roll','pitch','yaw','airspeed','groundspeed','alt','hdg','climb','xac','yac','zac','xmag','ymag','zmag','lat','lon','raw_alt','direction','speed']

def rvisualize (filename,outfile,param):
    data = pd.read_csv(filename,converters={'split':convert_time})

    #data=pd.read_csv('jakkur-loiter-test-sim10x.csv', sep=',',header=None,parse_dates=[0])
    data.columns = params_list
    data = data.drop(data.index[0])

    #converting datatypes into required formats
    data['Date'] = pd.to_datetime(data.Date)
    data['roll'] = pd.to_numeric(data.roll)
    data['pitch'] = pd.to_numeric(data.pitch)
    data['airspeed'] = pd.to_numeric(data.airspeed)
    data['alt'] = pd.to_numeric(data.alt)
    data['hdg'] = pd.to_numeric(data.hdg)
    data['climb'] = pd.to_numeric(data.climb)
    data['xac'] = pd.to_numeric(data.xac)
    data['yac'] = pd.to_numeric(data.yac)
    data['zac'] = pd.to_numeric(data.zac)
    data['xmag'] = pd.to_numeric(data.xmag)
    data['ymag'] = pd.to_numeric(data.ymag)
    data['zmag'] = pd.to_numeric(data.zmag)
    data['lat'] = pd.to_numeric(data.lat)
    data['lon'] = pd.to_numeric(data.lon)
    data['raw_alt'] = pd.to_numeric(data.raw_alt)
    data['direction'] = pd.to_numeric(data.direction)
    data['speed'] = pd.to_numeric(data.speed)

    #plotting the data
    #sb.lineplot(x="time", y="alt", data=data)
    sb.lineplot (x = "time",y = param,data = data)
    plt.savefig(outfile)
    return 0
