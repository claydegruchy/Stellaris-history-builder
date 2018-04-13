import json
import argparse
from jsondiff import diff
from viewSave import PrettyPrintJson, sortList, full_stack
import operator
import itertools

parser = argparse.ArgumentParser(description='Stellaris save file trend tracker and differ')
requiredNamed = parser.add_argument_group('Required named arguments')
requiredNamed.add_argument('-i', '--inputSave', help='Input file name', required=False)
#parser.parse_args(['-h'])
args = vars(parser.parse_args())


def traverse(dict_or_list, path=[]):
    if isinstance(dict_or_list, dict):
        iterator = dict_or_list.iteritems()
    else:
        iterator = enumerate(dict_or_list)
    for k, v in iterator:
        yield path + [k], v
        if isinstance(v, (dict, list)):
            for k, v in traverse(v, path + [k]):
                yield k, v


def buildText(location, newValue, oldValue=""):
	if not oldValue:
		return "{location} has been added, with a value of {newValue}".format( location=location, newValue=newValue)

	if isinstance(oldValue, (int, float)) and isinstance(newValue, (int, float)):
		difference = int(round(newValue)) - int(round( oldValue))
		percent = int(round(((float((newValue))/float(( oldValue)))*100) -100))

		if difference < 0:
			"{location}"
			response =  "{location} has fallen by {difference} to {newValue} from {oldValue} ({percent}%)".format( location=location, difference=abs(difference), newValue=newValue, oldValue=oldValue, percent=percent)
		else:
			response =  "{location} has risen by {difference} to {newValue} from {oldValue} (+{percent}%)".format( location=location, difference=abs(difference), newValue=newValue, oldValue=oldValue, percent=percent)
	elif isinstance(oldValue, (str, unicode)) and isinstance(newValue, (str, unicode)):
		response = "{location} has changed to {newValue} from {oldValue}".format( location=location, newValue=newValue, oldValue=oldValue)
	else:
		print type(location), type(newValue), type(oldValue)
		response = "{location} has changed to {newValue} from {oldValue}".format( location=location, newValue=newValue, oldValue=oldValue)
	return str(response)

def dd(d1, d2, ctx="", prefix="", multiplier=1):
    print prefix + "Changes in " + str(ctx)
    prefix = prefix * multiplier
    for k in d1:
        if k not in d2:
            print prefix + k + " is not present this month."
    for k in d2:
        if k not in d1:
            print prefix + k + " added this month"
            #print searchSubitem(d2[k], k)
            continue
        if d2[k] != d1[k]:
            if type(d2[k]) not in (dict, list):
                print prefix + buildText(k, d2[k], d1[k])
            else:
                if type(d1[k]) != type(d2[k]):
                    print prefix + buildText(k, d2[k], d1[k])
                    continue
                elif type(d2[k]) == list:
    				dd(list_to_dict(d1[k]), list_to_dict(d2[k]), k, prefix, 2)
                else:
				    if type(d2[k]) == dict:
				        dd(d1[k], d2[k], k, prefix, 2)
				        continue
    print prefix + "Done with changes in " + ctx
    return

def searchSubitem(d, k=None):
	if isinstance(d, dict):
		for item in d:
			if isinstance(d[item], dict):
				searchSubitem(d[item], d)
			elif isinstance(d, list):
				searchSubitem(list_to_dict(d), k)
			else:
				return buildText(item, d[item])
	elif isinstance(d, list):
		searchSubitem(list_to_dict(d), k)
	elif k:
		return k
	else:
		exit()


def list_to_dict(l):
	if not l:
		return {}
	try:
		if not isinstance(l, list):
			return {}
		if 'system' in l[0]:
			new_dict = {}
			for item in l:
			   name = item.pop('system')
			   new_dict[name] = item
			return new_dict
		else:
			return dict(itertools.izip_longest(*[iter(l)] * 2, fillvalue=""))
	except:
		#print l
		#print full_stack()
		return {}




if __name__ == '__main__':
	file = open(args['inputSave'], 'r').read()
	timeline = json.loads(file)
	timeList = []
	for date in timeline:
		if not timeline[date]:
			continue
		#print date
		timeline[date]['date'] = date
		timeList.append(timeline[date])
	timeList.sort(key=operator.itemgetter('date'))


	for i in xrange(len(timeList)):
		print i, len(timeList)
		if i+1 >= len(timeList):
			break
		print "Checking time range between", timeList[i]['currentDate'], timeList[i+1]['currentDate']
		dd(timeList[i], timeList[i+1], "", " ")
	exit()
	#thisDiff = json.loads( diff(firstDate, secondDate, dump=True, syntax='symmetric'))
	#for item in thisDiff:

	#	metaFields = ['$insert', '$delete', 'date']
	#	if any(x in item for x in metaFields):
	#		print "meta field detected:", item
	#		continue
		#print item


