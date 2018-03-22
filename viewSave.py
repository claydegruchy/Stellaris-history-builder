import json
from subprocess import Popen, PIPE
import zipfile
import os
import dateutil.parser as dparser
from jsondiff import diff
import time
import argparse


defaultBlockLocation = 'blocks/'
parser = argparse.ArgumentParser(
    description='Stellaris save file dissector and interpreter')
parser.add_argument(
    '-d',
    '--dissect',
    help='Split a save file into parts of examination, be sure to incude the directory',
    default=None)
parser.add_argument(
    '-dir',
    '--directory',
    help='parses all files in a given directory',
    default=None)
requiredNamed = parser.add_argument_group('Required named arguments')
requiredNamed.add_argument('-i', '--inputSave', help='Input file name')
requiredNamed.add_argument(
    '-b',
    '--blockfolder',
    help='Directory to store each parsed save.json (default = {defaultBlock})'.format(
        defaultBlock=defaultBlockLocation),
    default=defaultBlockLocation)
# parser.parse_args(['-h'])
args = vars(parser.parse_args())


stardateBlockTargetDirectory = args['blockfolder']


# effiency and debugging tools
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print '%s function took %0.3f ms' % (f.func_name, (time2 - time1) * 1000.0)
        return ret
    return wrap


def full_stack():
    import traceback
    import sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is None:  # i.e. if an exception is not present
        del stack[-1]	   # remove call of full_stack, the printed exception
        # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
        stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr


#####


def extractGamestate(path):
    # randomly generate temp filename
    try:
        #filename = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        filename = str(dparser.parse(path, fuzzy=True).date())
        save = zipfile.ZipFile(path)
        f = save.open('gamestate')
        s = str(f.read()).replace("\\\"", "")
        print "removed invalid characters"
        f.close()
        file = open(filename, 'w')
        file.write(s)
        file.close()
        return filename
    except Exception as e:
        print e
        exit()


def sendToParser(inFileName, outFileName):
    print "Sending file to parser. This may take some time depending on save size.", inFileName, outFileName
    p = Popen(['node', "extractSave.js", inFileName, outFileName],
              stdin=PIPE, stdout=PIPE, stderr=PIPE)
    print "Waiting on parser..."
    output, err = p.communicate(
        b"input data that is passed to subprocess' stdin")
    p.wait()
    p.returncode
    return output


def ExtractSave(filename):
    try:
        gamestate = extractGamestate(filename)
        outputFilename = stardateBlockTargetDirectory + gamestate + '.json'
        if os.path.isfile(outputFilename):
            print "File already parsed, skipping"
        else:
            print sendToParser(inFileName=gamestate, outFileName=outputFilename)
        os.remove(gamestate)
        saveJson = open(outputFilename, 'r').read()
        saveJson = json.loads(saveJson)
        return saveJson
    except Exception as e:
        print e.message, e.args
        exit()


def SaveFile(path, filename, content):
    print "Saving file", filename
    fullName = os.path.join(path, filename)
    savefile = open(fullName, 'w')
    savefile.write(content)
    savefile.close()
    return savefile


def PrettyPrintJson(data):
    return json.dumps(data, indent=4, sort_keys=True)


def DissectSave(data, directory='extract'):
    for item in data:
        SaveFile(directory, item, PrettyPrintJson(saveData[item]))


globalCivReference = {}


def CivLookup(saveData, civNumber):
    for item in saveData['country']:
        if item.isdigit():
            try:
                if item != str(civNumber):
                    continue
                return saveData['country'][item]['name']
            except BaseException:
                continue


def PlanetLookup(saveData, planetID):
    galactic_object = saveData['galactic_object']
    for system in galactic_object:
        try:
            if int(planetID) in galactic_object[system]['planet']:
                return galactic_object[system]['name']
        except BaseException:
            continue
    return "Unknown planet"


def ListToSingle(arg):
    if not isinstance(arg, (list, tuple)):
        arg = [arg]
    return arg[0]


def WarParticipantLookup(warValue, saveData, key):
    offenderList = []
    for offender in warValue[key]:
        offenderList.append(offender['country'])
    return offenderList


def WarExhaustionCalculator():
    # wip
    return


def WarLookup(saveData, country):
    warObject = {}
    warMap = saveData['war']
    for war in warMap:
        try:
            ThisWarsAttackers = WarParticipantLookup(
                warMap[war], saveData, 'attackers')
            if int(country) in ThisWarsAttackers:
                ThisWarsDefenders = WarParticipantLookup(
                    warMap[war], saveData, 'defenders')
                warObject['offensiveWars'] = {}
                #warAddress = warObject['offensiveWars'][warMap[war]['name']]
                warObject['offensiveWars'][warMap[war]['name']] = {
                    "attackers": [CivLookup(saveData, x) for x in ThisWarsAttackers],
                    "defenders": [CivLookup(saveData, x) for x in ThisWarsDefenders],
                    "attackerWarGoals": warMap[war]['attacker_war_goal']['type'],
                    "defenderWarGoals": warMap[war]['defender_war_goal']['type']
                }
                warObject['offensiveWars'][warMap[war]['name']]['battles'] = {}
                try:
                    for battle in warMap[war]['battles']:
                        ThisBattle = {}
                        if battle['attacker_victory']:
                            warObject['offensiveWars'][warMap[war]['name']
                                                       ]['battles']['attackerVictories'] = []
                            ThisBattle['system'] = saveData['galactic_object'][str(
                                battle['planet'])]['name']

                            warObject['offensiveWars'][warMap[war]['name']
                                                       ]['battles']['attackerVictories'].append(ThisBattle)
                        else:
                            warObject['offensiveWars'][warMap[war]['name']
                                                       ]['battles']['defenderVictories'] = []
                            ThisBattle['system'] = saveData['galactic_object'][str(
                                battle['planet'])]['name']

                            warObject['offensiveWars'][warMap[war]['name']
                                                       ]['battles']['defenderVictories'].append(ThisBattle)
                    # sort items with
                    # list_of_dicts.sort(key=operator.itemgetter('name'))
                except BaseException:
                    print "Could not find battles"
        except BaseException:
            print full_stack()
            print "Could not interpret agro war"
        try:
            ThisWarsDefenders = WarParticipantLookup(
                warMap[war], saveData, 'defenders')
            if int(country) in ThisWarsDefenders:
                ThisWarsAttackers = WarParticipantLookup(
                    warMap[war], saveData, 'attackers')
                warObject['defensiveWars'] = {}
                warObject['defensiveWars'][warMap[war]['name']] = {
                    "attackers": [CivLookup(saveData, x) for x in ThisWarsAttackers],
                    "defenders": [CivLookup(saveData, x) for x in ThisWarsDefenders],
                    "attackerWarGoals": warMap[war]['attacker_war_goal']['type'],
                    "defenderWarGoals": warMap[war]['defender_war_goal']['type']
                }

        except BaseException:
            print "Could not interpret def war"
        # todo here:
        # battle lookup
        # war exhaustion
    return warObject


def InformationMap(saveData, country):

    MonthReport = {}

    countryMap = saveData['country'][country]
    # income amounts
    standard_economy_module = countryMap['modules']['standard_economy_module']
    monthlyResources = {}
    for resource in standard_economy_module['last_month']:
        monthlyResources[resource] = ListToSingle(
            standard_economy_module['last_month'][resource])
    MonthReport['monthlyResources'] = monthlyResources

    #amount in bank
    bankedResources = {}
    for resource in standard_economy_module['resources']:
        bankedResources[resource] = ListToSingle(
            standard_economy_module['resources'][resource])
    MonthReport['bankedResources'] = bankedResources

    # owned systems
    MonthReport['controlledSystems'] = []
    for planet in countryMap['controlled_planets']:
        MonthReport['controlledSystems'].append(PlanetLookup(saveData, planet))
    MonthReport['controlledSystems'] = list(
        set(MonthReport['controlledSystems']))
    #	captial system:
    MonthReport['capitalSystem'] = PlanetLookup(
        saveData, countryMap['capital'])
    # goverment types
    #MonthReport['govermentType'] = countryMap['goverment']['type']

    # wars
    MonthReport['wars'] = WarLookup(saveData, country)

    '''
	#	attackers/defenders - compute owner
	#warMap['attackers'][i]['country']
	#warMap['defenders'][i]['country']
	#	battles
	#warMap['battles']

	#	#claims - compute owner
	saveData['galactic_object'][item]['claims'][i]
	#options of everyone
	saveData['country'][country]['ai']['attitude']
	#	#rivalries
	saveData['country'][country]['standard_diplomacy_module']['rivals'][i]
	#fleet sizes

	#leaders
	saveData['leaders'][leaderNumber]
	#trade deals
	trade_deals = saveData['trade_deal'][number]
	#first party:
	trade_deals['first']['country']
	#second party:
	trade_deals['second']['country']
	#alliances
	alliance = saveData['alliance'][number]
	#name:
	alliance['name']
	alliance['members'][i]
	#big events (crises)

	#tech level-diff
	saveData['country'][country]['tech_status']['technology']
	#asension perks-diff

	#notable polacy changes - diff
	saveData['country'][country]['active_policies']
	'''
    return MonthReport


def InterpretSave(saveData):
    currentDate = str(dparser.parse(saveData['date'], fuzzy=True).date())

    months = {
        currentDate: {}
    }

    for country in saveData['country']:
        try:
            countryName = saveData['country'][country]['name']
            months[currentDate][countryName] = InformationMap(
                saveData,
                country)

        except Exception:
            # print full_stack()
            continue

    return months


if __name__ == '__main__':

    if args['dissect']:
        print 'Dissecting save file to', args['dissect']
        print 'Loaded save file', args['inputSave']
        saveData = ExtractSave(args['inputSave'])
        for item in saveData:
            SaveFile(args['dissect'], item, PrettyPrintJson(saveData[item]))
        exit()
    if args['directory']:
        print 'Loading saves from', args['directory']
        timeline = {}
        for filename in os.listdir(args['directory']):
            if filename.endswith(".sav"):
                print 'Loading save file', filename
                saveData = ExtractSave(args['directory'] + filename)
                timeline.update(InterpretSave(saveData))
            else:
                continue
        print PrettyPrintJson(timeline)
        exit()
    else:
        if args['inputSave']:
            print 'Loaded save file', args['inputSave']
            saveData = ExtractSave(args['inputSave'])
            print PrettyPrintJson(InterpretSave(saveData))
            exit()

    # print json.dumps(diff(saveData1['country']['1']
    # ,saveData2['country']['1'] ))
    exit()
