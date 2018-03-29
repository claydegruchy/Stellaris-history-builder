import json
from subprocess import Popen, PIPE
import zipfile
import os
import dateutil.parser as dparser
import time
import argparse
import operator


defaultBlockLocation = 'blocks/'
parser = argparse.ArgumentParser(description='Stellaris save file dissector and interpreter')
parser.add_argument('-d', '--dissect', help='Split a save file into parts of examination, be sure to incude the directory', default=None)
parser.add_argument('-dir', '--directory', help='parses all files in a given directory', default=None)
requiredNamed = parser.add_argument_group('Required named arguments')
requiredNamed.add_argument('-i', '--inputSave', help='Input file name')
requiredNamed.add_argument('-b', '--blockfolder', help='Directory to store each parsed save.json (default = {defaultBlock})'.format(defaultBlock=defaultBlockLocation), default=defaultBlockLocation)
#parser.parse_args(['-h'])
args = vars(parser.parse_args())



stardateBlockTargetDirectory = args['blockfolder']


#issues:
'''
issue in 2301.08.26.sav, wars not working
'''

#todo:
'''
include something like https://github.com/mewwts/addict for better parsing
'''

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

def sortList(l, k, r=False):
	return sorted(l, key=operator.itemgetter(k), reverse=r)


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

def SystemOwnerLookup(saveData, systemName):
	for country in saveData['country'] :
		try:
			for planet in saveData['country'][country]['controlled_planets']:
				if SystemSearch(saveData, planet) == systemName:
					return CivLookup(saveData, country)
		except:
			#This catches fake countries
			continue
	return "No Owner"

def SystemSearch(saveData, planetID=None, systemID=None):
	galactic_object = saveData['galactic_object']
	if systemID:
		return galactic_object[str(systemID)]['name']
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


def WarLookup(saveData, country):
	warObject = {}
	warMap = saveData['war']
	for war in warMap:
		warType = None
		try:
			ThisWarsAttackers = WarParticipantLookup(warMap[war], saveData, 'attackers')
			if int(country) in ThisWarsAttackers:
				warType = 'offensiveWars'
				ThisWarsDefenders = WarParticipantLookup(warMap[war], saveData, 'defenders')
				warObject['offensiveWars'] = {}
				#warAddress = warObject['offensiveWars'][warMap[war]['name']]
				warObject['offensiveWars'][warMap[war]['name']] = {
				"attackers": [ CivLookup(saveData, x) for x in ThisWarsAttackers ],
				"defenders": [ CivLookup(saveData, x) for x in ThisWarsDefenders ],
				"attackerWarGoals": warMap[war]['attacker_war_goal']['type'],
				"defenderWarGoals": warMap[war]['defender_war_goal']['type']
				}
		except BaseException:
			print full_stack()
			print "Could not interpret agro war"


		try:
			ThisWarsDefenders = WarParticipantLookup(warMap[war], saveData, 'defenders')
			if int(country) in ThisWarsDefenders:
				warType = 'defensiveWars'
				ThisWarsAttackers = WarParticipantLookup(warMap[war], saveData, 'attackers')
				warObject['defensiveWars'] = {}
				warObject['defensiveWars'][warMap[war]['name']] = {
				"attackers": [ CivLookup(saveData, x) for x in ThisWarsAttackers ],
				"defenders": [ CivLookup(saveData, x) for x in ThisWarsDefenders ],
				"attackerWarGoals": warMap[war]['attacker_war_goal']['type'],
				"defenderWarGoals": warMap[war]['defender_war_goal']['type']
				}

		except BaseException:
			print "Could not interpret def war"


		try:
			if 'battles' not in warMap[war] :
				pass
			elif not warType :
				pass#print "This war is not relevant"
			elif not warMap[war]['battles']:
				pass
			else:
				if 'battles' not in warObject[warType][warMap[war]['name']]:
					warObject[warType][warMap[war]['name']]['battles'] = {}
				warObject[warType][warMap[war]['name']]['attackerExhaustionTotal'] = 0
				warObject[warType][warMap[war]['name']]['defenderExhaustionTotal'] = 0
				for battle in warMap[war]['battles']:
					ThisBattle = {}
					ThisBattle['attackerExhaustion'] = (round(battle['attacker_war_exhaustion'] * 100, 2))
					warObject[warType][warMap[war]['name']]['attackerExhaustionTotal'] += ThisBattle['attackerExhaustion']
					ThisBattle['defenderExhaustion'] = (round(battle['defender_war_exhaustion'] * 100, 2))
					warObject[warType][warMap[war]['name']]['defenderExhaustionTotal'] += ThisBattle['defenderExhaustion']
					if battle['system'] and battle['system'] != 4294967295:
						ThisBattle['system'] = SystemSearch(saveData, planetID=None, systemID=battle['system'])
					if battle['attacker_victory'] == True:
						if 'attackerVictories' not in warObject[warType][warMap[war]['name']]['battles']:
							warObject[warType][warMap[war]['name']]['battles']['attackerVictories'] = []
						warObject[warType][warMap[war]['name']]['battles']['attackerVictories'].append(ThisBattle)
					else:
						#finding system name is hard #ThisBattle['system'] = saveData['galactic_object'][str(battle['planet'])]['name']
						if 'defenderVictories' not in warObject[warType][warMap[war]['name']]['battles']:
							warObject[warType][warMap[war]['name']]['battles']['defenderVictories'] = []
						warObject[warType][warMap[war]['name']]['battles']['defenderVictories'].append(ThisBattle)
			#sort items with list_of_dicts.sort(key=operator.itemgetter('name'))
		except:
			print "Could not find battles", warMap[war]['name']
			print full_stack()
	return warObject



def ClaimLookup(saveData, country):
	ClaimList = []

	for system in saveData['galactic_object']:
		try:
			if 'claims' not in saveData['galactic_object'][system]:
				continue
			for claim in saveData['galactic_object'][system]['claims']:
				if claim['owner'] == int(country):
					ClaimInstance = {}
					ClaimInstance['system'] = SystemSearch(saveData, planetID=None, systemID=system)
					ClaimInstance['currentOwner'] = SystemOwnerLookup(saveData, ClaimInstance['system'])
					ClaimList.append(ClaimInstance)
		except BaseException:
			print full_stack()
			continue
	return sortList(ClaimList, "system")

def FleetsLookup(saveData, country, specificShip=None, admirals=None):
	fleetsList = {}
	for fleet in saveData['fleet']:
		fleetInstance = {}
		try:
			requiredFields = ['owner','name']
			if not any(x in saveData['fleet'][fleet] for x in requiredFields):
				continue
			unrequiredFields = ['station','civilian']
			if any(x in saveData['fleet'][fleet] for x in unrequiredFields):
				continue
			if not specificShip:
				if 'transport' in saveData['fleet'][fleet]['name'].lower():
					continue
			if saveData['fleet'][fleet]['owner'] == int(country):
				fleetInstance['ships'] = len(saveData['fleet'][fleet]['ships'])
				if admirals:
					for admiral in admirals:
						if admirals[admiral]['location'] == saveData['fleet'][fleet]['name']:
							fleetInstance['admiral'] = admirals[admiral]['name']
				fleetsList[saveData['fleet'][fleet]['name']] = fleetInstance
				if specificShip in saveData['fleet'][fleet]['ships']:
					return saveData['fleet'][fleet]['name']
		except:
			print full_stack()
	if specificShip:
		return "Unknown Space Fleet"
	return fleetsList

def LeadersLookup(saveData, country, leaderType, specificLeader=None):
	#leaderTypes: admiral, general, governor, ruler, scientist
	leaderList = {}
	for leader in saveData['leaders']:
		try:
			leaderInstance = {}
			#print saveData['leaders'][leader]['country'], country
			if saveData['leaders'][leader]['country'] == int(country):
				if saveData['leaders'][leader]['class'] == leaderType:

					if isinstance(saveData['leaders'][leader]['roles'][leaderType]['trait'], (list, tuple)):
						leaderInstance['traits'] = saveData['leaders'][leader]['roles'][leaderType]['trait']
					else:
						leaderInstance['traits'] = [saveData['leaders'][leader]['roles'][leaderType]['trait']]
					leaderInstance['level'] = saveData['leaders'][leader]['level']
					leaderInstance['name'] = " ".join(saveData['leaders'][leader]['name'].values())

					if specificLeader:
						if int(specificLeader) == int(leader):
							return leaderInstance['name']

					if 'ship' in saveData['leaders'][leader]['location']:
						leaderInstance['location'] = FleetsLookup(saveData, country, specificShip=saveData['leaders'][leader]['location']['ship'])
					else:
						leaderInstance['location'] = SystemSearch(saveData, saveData['leaders'][leader]['location']['planet'])
					leaderInstance['age'] = saveData['leaders'][leader]['age']
					if sum(map(int, list(str(abs(sum([ord(char) - 96 for char in leaderInstance['name'].lower()]))))[:2])) == 7:
						leaderInstance['gender'] = "Genderless"
					else:
						leaderInstance['gender'] = saveData['leaders'][leader]['gender']
					leaderList[leaderInstance['name']] = leaderInstance
		except:
			#print country
			#print full_stack()
			continue
	if specificLeader:
		return "No leader"
	return leaderList


def TechnologyLookup(saveData, country):
	countryData = saveData['country'][country]
	techMap = countryData['tech_status']
	technologyObject = {}
	technologyObject['engineering'] = {}
	technologyObject['physics'] = {}
	technologyObject['society'] = {}
	requiredFields = ['engineering','physics','society']
	for researcherType in requiredFields:
		if researcherType not in techMap['leaders']:
			techMap['leaders'][researcherType] = "No leader"
	for field, leader in techMap['leaders'].iteritems():
		technologyObject[field]['researcher'] = LeadersLookup(saveData, country, leaderType='scientist', specificLeader=leader)

	if 'engineering_queue' in techMap:
		technologyObject['engineering']['currentResearch'] = [x['technology'] for x in techMap['engineering_queue'] if 'technology' in x][0]
	else:
		technologyObject['engineering']['currentResearch'] = None

	if 'physics_queue' in techMap:
		technologyObject['physics']['currentResearch'] = [x['technology'] for x in techMap['physics_queue'] if 'technology' in x][0]
	else:
		technologyObject['physics']['currentResearch'] = None

	if 'society_queue' in techMap:
		technologyObject['society']['currentResearch'] = [x['technology'] for x in techMap['society_queue'] if 'technology' in x][0]
	else:
		technologyObject['society']['currentResearch'] = None
	technologyObject['completedResearch'] = techMap['technology']

	return technologyObject

def InformationMap(saveData, country):

	MonthReport = {}
	print "parsing", saveData['country'][country]['name']

	countryMap = saveData['country'][country]
	# income amounts
	standard_economy_module = countryMap['modules']['standard_economy_module']
	monthlyResources = {}
	for resource in standard_economy_module['last_month']:
		monthlyResources[resource] = ListToSingle(standard_economy_module['last_month'][resource])
	MonthReport['monthlyResources'] = monthlyResources

	#amount in bank
	bankedResources = {}
	for resource in standard_economy_module['resources']:
		bankedResources[resource] = ListToSingle(standard_economy_module['resources'][resource])
	MonthReport['bankedResources'] = bankedResources

	# owned systems
	MonthReport['controlledSystems'] = []
	for planet in countryMap['controlled_planets']:
		MonthReport['controlledSystems'].append(SystemSearch(saveData, planet))
	MonthReport['controlledSystems'] = list(
		set(MonthReport['controlledSystems']))
	#	captial system:
	MonthReport['capitalSystem'] = SystemSearch(
		saveData, countryMap['capital'])
	# goverment types
	MonthReport['govermentType'] = countryMap['government']['type']

	# wars
	MonthReport['wars'] = WarLookup(saveData, country)

	MonthReport['claims'] = ClaimLookup(saveData, country)



	MonthReport['opinons'] = {}
	for item in countryMap['ai']['attitude']:
		MonthReport['opinons'][CivLookup(saveData, item['country'])] = item['attitude']

	MonthReport['rivals'] = []
	if 'rivals' in countryMap['modules']['standard_diplomacy_module']:
		for rival in countryMap['modules']['standard_diplomacy_module']['rivals']:
			MonthReport['rivals'].append(CivLookup(saveData, rival))

	#we are going to cheat here and misassign leaders.
	#This makes for better story telling and I cant figure out how its supposed to work

	MonthReport['leaders'] = {}
	MonthReport['leaders']['admirals'] = LeadersLookup(saveData, country, leaderType='admiral')
	MonthReport['leaders']['generals'] = LeadersLookup(saveData, country, leaderType='general')
	MonthReport['leaders']['governors'] = LeadersLookup(saveData, country, leaderType='governor')
	MonthReport['leaders']['rulers'] = LeadersLookup(saveData, country, leaderType='ruler')
	MonthReport['leaders']['scientists'] = LeadersLookup(saveData, country, leaderType='scientist')

	MonthReport["millitary"] =  {}
	MonthReport["millitary"]['fleets'] = FleetsLookup(saveData, country, admirals=MonthReport['leaders']['admirals'])
	MonthReport["millitary"]['totalStrength'] =  countryMap['military_power']

	MonthReport['tradeDeals'] = []
	for deal in saveData['trade_deal'] :
		dealInstance = {}
		thisDeal = saveData['trade_deal'][deal]
		if thisDeal['first']['country'] == int(country) or thisDeal['second']['country'] == int(country):
			dealInstance['length'] = thisDeal['length']
			dealInstance['initiator'] = CivLookup(saveData, thisDeal['first']['country'])
			dealInstance['partner'] =  CivLookup(saveData, thisDeal['second']['country'])
			MonthReport['tradeDeals'].append(dealInstance)
			#todo: add the contents of the trade deal

	MonthReport['allianceMembership'] = {}
	for alliance in saveData['alliance']:
		allianceMap = {}
		thisAlliance = saveData['alliance'][alliance]
		membershipFields = ['associates','members']
		for field in membershipFields:
			allianceMap[field] = [CivLookup(saveData, x) for x in thisAlliance[field]]
			if int(country) in thisAlliance[field]:
				allianceMap['leader'] = CivLookup (saveData, thisAlliance['leader'])
				allianceMap['ourMembershipType'] = field
				MonthReport['allianceMembership'][thisAlliance['name']] = allianceMap

	MonthReport['technology'] = TechnologyLookup(saveData, country)
	#todo: add special project tracker

	if 'ascension_perks' in countryMap:
		MonthReport['ascensionPerks'] = countryMap['ascension_perks']

	MonthReport['policies'] = {}
	for policy in countryMap['active_policies']:
		policy['policy']
		MonthReport['policies'][policy['policy']] = policy['selected']


	'''
	todo:
	#big events (crises)
	'''
	print "successfully parsed", saveData['country'][country]['name']
	print "######"
	return MonthReport


def InterpretSave(saveData):
	currentDate = str(dparser.parse(saveData['date'], fuzzy=True).date())
	print currentDate
	thisSave = {}
	thisSave['currentDate'] = currentDate
	for country in saveData['country']:
		if 'name' not in saveData['country'][country]:
			continue
		try:
			print saveData['country'][country]['name']
			countryName = saveData['country'][country]['name']
			thisSave[countryName] = InformationMap(
				saveData,
				country)

		except Exception:
			print full_stack()
			continue

	return thisSave


if __name__ == '__main__':

	if args['dissect']:
		print 'Dissecting save file to', args['dissect']
		print 'Loaded save file', args['inputSave']
		saveData = ExtractSave(args['inputSave'])
		for item in saveData:
			SaveFile(args['dissect'], item, PrettyPrintJson(saveData[item]))
	if args['directory']:
		print 'Loading saves from', args['directory']
		timeline = {}
		for filename in os.listdir(args['directory']):
			if filename.endswith(".sav"):
				print 'Loading save file', filename
				saveData = ExtractSave(args['directory']+filename)
				interpretedSave = InterpretSave( saveData)
				print interpretedSave['currentDate']
				timeline[interpretedSave['currentDate']] = interpretedSave
				#timeline.sort(key=operator.itemgetter('currentDate'))
			else:
				continue
		SaveFile(path=args['directory'], filename="timeline.json", content=json.dumps(timeline))
		exit()
	else:
		if args['inputSave']:
			print 'Loaded save file', args['inputSave']
			saveData = ExtractSave(args['inputSave'])
			#print PrettyPrintJson( WarLookup(saveData, "4"))
			#print PrettyPrintJson (InterpretSave(saveData))
			print PrettyPrintJson( InformationMap(saveData, "0"))
			#print PrettyPrintJson(TechnologyLookup(saveData, "8"))
			#print PrettyPrintJson( LeadersLookup(saveData, "0", leaderType="scientist", specificLeader="410"))
			exit()

	exit()

