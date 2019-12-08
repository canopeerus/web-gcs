import datetime

def dateTimeMerge (date_str,time_str):
    return datetime.strptime (date_str + ' ' + time_str,'%Y-%m-%d %I:%M:%p')

def getCoordsFloatList (coords_str):
    return list (map (float, coords_str_list.split(',')))
