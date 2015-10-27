from json import load
import requests
import codecs
import unicodecsv as csv
import re

# get ank-themas.json from 

with open('ank-themas.json', 'r') as f:
	themes = load(f)['atlas.themas']

ank_f = open('ank.csv', 'w')
writer = csv.writer(ank_f, delimiter=';')
writer.writerow("naam", "samenvatting", "thema", "thema samenvatting", "onderwerp", "type", "eigenaar", "service type", "data url", "kaart url", "laagnaam")

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
		type_ = indicator['type']

		map_url = indicator['uiKaartProxy']['mapUrl']
		layer = indicator['uiKaartProxy']['layerName']
		data_owner = indicator['uiKaartProxy']['bronhouderNaam']
		service_type = indicator['uiKaartProxy']['serviceType']

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
				print "Error: indicator has no Over de Kaart tab"
				print content
				failed_url.append([name, theme_name, 'missing map info tab'])

			if len(map_info) > 0:
				url_re = re.search('(?<=<\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				print re.findall('(?<=<\/strong>)http:\/\/[^c].+?(?=<br \/>)', map_info)

				if url_re != None:
					url = url_re.group(0)
				else:
					print "Failed to find URL... "
					failed_url.append([name, theme_name, 'no data url found in info tab'])

				try:
					with codecs.open('bijsluiters/%s_%s.html' % (name, theme_name), 'w', encoding='utf8') as f:
						f.write(map_info)

				except IOError:
					print "Error, can't save friendly name as it contains illegal characters..."
					print "Saving indicator id instead..."
					with codecs.open('bijsluiters/%s.html' % (id_), 'w', encoding='utf8') as g:
						g.write(map_info)
			else:
				print "Error: empty Over de Kaart tab"
				failed_url.append([name, theme_name, 'empty map info tab'])
		else:
			print "Error: server returned 404. %s has no bijsluiter... ?" % name
			failed_url.append([name, theme_name, 'missing bijsluiter'])


		row = [name, summary, theme_name, theme_summary, subject, type_, data_owner, service_type, data_url, map_url, layer]
		
		# try:
		writer.writerow(row)
		# except UnicodeEncodeError:
		# 	print "Warning... encountered Unicode Encoding error, dumping to ank-broken.csv"
		# 	broken_f.write('%s;%s\n' % (name, theme_name))

with open('failed_urls.csv', 'w') as f:
	for url in failed_url:
		f.write('%s;%s;%s\n' % tuple(url))

ank_f.close()
# broken_f.close()

