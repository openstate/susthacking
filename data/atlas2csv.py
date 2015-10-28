from json import load
import requests
import codecs
import unicodecsv as csv
import re
from bs4 import BeautifulSoup as BS

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
		
		r = requests.get(wfs_url + limit)
		if r.status_code == 200:
			try:
				a = r.json()
				return wfs_url, error 

			except ValueError:
				soup = BS(r.text, 'xml')
				error = soup.find('ExceptionText').string

				return wfs_url, error
		else:
			error = "HTTP 404"
			return wfs_url, error
	else:
		return url, error


# get ank-themas.json from initial ANK map viewer requests
# http://www.atlasnatuurlijkkapitaal.nl/kaarten?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getThemas&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1
with open('ank-themas.json', 'r') as f:
	themes = load(f)['atlas.themas']

ank_f = open('ank.csv', 'w')
writer = csv.writer(ank_f, delimiter=';')
writer.writerow(["naam", "samenvatting", "thema", "onderwerp", "eigenaar", "data url", "data url error", "kaart url", "laagnaam"])

# broken_f = codecs.open('ank-broken.csv', 'w', encoding='utf8')

failed_url = []

for theme in themes:
	theme_name = theme['naam']
	theme_summary = theme['samenvatting']

	indicators = theme['childIndicators']

	for indicator in indicators:
		id_ = indicator['id']
		name = indicator['naam']
		summary = indicator['samenvatting']
		subject = indicator['onderwerp']
		# type_ = indicator['type']

		map_url = indicator['uiKaartProxy']['mapUrl']
		layer = indicator['uiKaartProxy']['layerName']
		data_owner = indicator['uiKaartProxy']['bronhouderNaam']
		# service_type = indicator['uiKaartProxy']['serviceType']

		#test if service returns sane Capabilities document
		# TODO

		# request for bijsluiter seems to be the same for every indicator
		# hence we call it and input the indicator's id_

		data_url = ""

		# print "Processing", name, theme_name

		r = requests.get("http://www.atlasnatuurlijkkapitaal.nl/kaarten?p_p_id=atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getBijsluiters&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_count=1&_atlasMap_WAR_atlasfrontendportlet_INSTANCE_FotTSS5BXAUh_epsg=28992&indicatorId=%s&x=176988.16&y=493008&epsg=28992" % id_) 
		if r.status_code == 200:
			bijsluiter = r.json()
			content = bijsluiter['bijsluiters'][0]

			try:
				map_info = content['bijsluiterTabs'][1]['tekst']
			except IndexError:
				print "Error: indicator has no 'Over de Kaart tab'"
				# print content
				failed_url.append([name, theme_name, 'missing map info tab'])

			if len(map_info) > 0:
				url_re = re.search('(?<=<\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				# print re.findall('(?<=<\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				if url_re != None:
					url = url_re.group(0)
					data_url, data_url_error = find_data(url, layer)
				else:
					print "Failed to find URL... "
					failed_url.append([name, theme_name, 'no data url found in info tab'])

				try:
					with codecs.open('bijsluiters/%s_%s.html' % (name, theme_name), 'w', encoding='utf8') as f:
						f.write(map_info)

				except IOError:
					print "Error, can't save bijsluiter with a friendly name as it contains illegal characters..."
					print "Saving indicator id instead..."
					with codecs.open('bijsluiters/%s.html' % (id_), 'w', encoding='utf8') as g:
						g.write(map_info)

				row = [name, summary, theme_name, subject, data_owner, data_url, data_url_error, map_url, layer]
				writer.writerow(row)

			else:
				print "Error: empty Over de Kaart tab"
				failed_url.append([name, theme_name, 'empty map info tab'])
		
		else:
			print "Error: server returned 404. %s has no bijsluiter... ?" % name
			failed_url.append([name, theme_name, 'missing bijsluiter'])

with open('failed_urls.csv', 'w') as f:
	for url in failed_url:
		f.write('%s;%s;%s\n' % tuple(url))

ank_f.close()