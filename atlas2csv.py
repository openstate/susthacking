from json import load
from bs4 import BeautifulSoup as BS
import os
import requests
import codecs
import unicodecsv as csv
import re

def find_data(url, layer):
	wfs_url = re.sub(re.compile(ur'wms', re.IGNORECASE), 'wfs', url)

	error = ""

	if 'wfs' in wfs_url or 'ows' in wfs_url:
		parameters = "SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=%s&OUTPUTFORMAT=json&SRSNAME=EPSG:4326" % layer
		limit = "&maxFeatures=1"

		if wfs_url[-1] == "?":
			wfs_url += parameters
		else:
			wfs_url += "?" + parameters
		
		try:
			r = requests.get(wfs_url + limit, timeout=5)
		except requests.exceptions.ConnectionError:
			return url, 'Niet gelukt om verbinding met server te maken'
		except requests.exceptions.Timeout:
			return url, 'Timeout na 5 seconden'

		if r.status_code == 200:
			try:
				a = r.json()
				return wfs_url, error 

			except ValueError:
				soup = BS(r.text, 'xml')
				error = soup.find('ExceptionText').string

				if 'unknown' in error:
					error = 'Deze databron is alleen als WMS beschikbaar, gebruik kaart url om gegevens op te halen'

				return '', error
		else:
			error = r.status_code
			return '', error
	else:
		return url, error


# get ank-themas.json from initial ANK map viewer requests
# http://www.atlasnatuurlijkkapitaal.nl/kaarten?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getThemas&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1

meta_url = {
	'ank': 'http://www.atlasnatuurlijkkapitaal.nl/kaarten?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getBijsluiters&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1&_atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh_epsg=28992&indicatorId=%s&x=176988.16&y=493008&epsg=28992',
	'alo': 'http://www.atlasleefomgeving.nl/kijken?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_Gs2j&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getBijsluiters&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=5&_atlasMap_WAR_atlasfrontendportlet_INSTANCE_Gs2j_epsg=28992&indicatorId=%s&x=160000&y=450000&epsg=28992'
}
# atlas = 'ank'
atlas = 'alo'

path_themas = os.path.join('data', atlas, 'themas.json')
path_out = os.path.join('data', atlas, '%s.csv' % atlas)
path_bijsluiters = os.path.join('data', atlas, 'bijsluiters')

ank_f = open(path_out, 'w')
writer = csv.writer(ank_f, delimiter=';')
writer.writerow(["naam", "samenvatting", "thema", "onderwerp", "eigenaar", "data url", "data url error", "kaart url", "laagnaam"])

with open(path_themas, 'r') as f:
	themes = load(f)['atlas.themas']

# broken_f = codecs.open('ank-broken.csv', 'w', encoding='utf8')
failed_url = []

for theme in themes:
	theme_name = theme['naam']
	theme_summary = theme['samenvatting']

	indicators = theme['childIndicators']

	for indicator in indicators:
		# use this id for ANK

		if atlas == 'alo':
			id_ = '-' + str(indicator['uiKaartProxy']['id'])
		else:
			id_ = indicator['id']
		name = indicator['naam']
		summary = indicator['samenvatting']
		subject = indicator['onderwerp']
		# type_ = indicator['type']

		# map_url = indicator['uiKaartProxy']['mapUrl']
		layer = indicator['uiKaartProxy']['layerName']
		data_owner = indicator['uiKaartProxy']['bronhouderNaam']		

		# service_type = indicator['uiKaartProxy']['serviceType']

		#test if service returns sane Capabilities document
		# TODO

		# request for bijsluiter seems to be the same for every indicator
		# hence we call it and input the indicator's id_

		data_url = ""

		# print "Processing", name, theme_name

		# url = "http://www.atlasnatuurlijkkapitaal.nl/kaarten?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getBijsluiters&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1&_atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh_epsg=28992&indicatorId=%s&x=176988.16&y=493008&epsg=28992" % id_
		# print meta_url[atlas] % id_
		r = requests.get(meta_url[atlas] % id_)

		if r.status_code == 200:
			bijsluiter = r.json()

			try:
				content = bijsluiter['bijsluiters'][0]
			except IndexError:
				print "Error %s has no bijsluiter (server returned 200)" % name 
				failed_url.append([name, theme_name, 'missing bijsluiter (200)'])
				continue

			map_info = ''
			try:
				map_info = content['bijsluiterTabs'][1]['tekst']
			except (IndexError, TypeError):
				print "Error: %s has no 'Over de Kaart tab'" % name
				# print content
				failed_url.append([name, theme_name, 'missing map info tab'])
				continue

			if len(map_info) > 0:
				url_re = re.search('(?<=dataset: <\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				# print re.findall('(?<=<\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				if url_re != None:
					url = url_re.group(0)
					data_url, data_url_error = find_data(url, layer)
				else:
					print "Failed to find data URL... "
					failed_url.append([name, theme_name, 'no data url found in info tab'])
					continue

				try:
					with codecs.open(path_bijsluiters +  '/%s_%s.html' % (name, theme_name), 'w', encoding='utf8') as f:
						f.write(map_info)

				except IOError:
					print "Error, can't save bijsluiter with a friendly name as it contains illegal characters..."
					print "Saving indicator id instead..."
					with codecs.open(path_bijsluiters + '/%s.html' % (id_), 'w', encoding='utf8') as g:
						g.write(map_info)

				parameters = "SERVICE=WMS&VERSION=1.0.0&REQUEST=GetMap&LAYERS=%s&STYLES=&BBOX=13014,306243,286599,623492&WIDTH=400&HEIGHT=500&FORMAT=image/png&SRS=EPSG:28992" % layer
				
				if url[-1] == "?":
					map_url = url + parameters
				else:
					map_url = url + "?%s" % parameters

				if 'pdf' in map_url: map_url = ""

				row = [name, summary, theme_name, subject, data_owner, '=HYPERLINK("%s")' % data_url, data_url_error, '=HYPERLINK("%s")' % map_url, layer]
				writer.writerow(row)

			else:
				print "Error: %s has an empty 'Over de Kaart' tab" % name
				failed_url.append([name, theme_name, 'empty map info tab'])
		
		else:
			print "Error: server returned 404. %s has no bijsluiter... ?" % name
			failed_url.append([name, theme_name, 'missing bijsluiter (404)' ])

# with open('failed_urls.csv', 'w') as f:
# 	for url in failed_url:
# 		f.write('%s;%s;%s\n' % tuple(url))

ank_f.close()