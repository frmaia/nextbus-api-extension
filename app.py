#!/usr/bin/python

from flask import Flask, redirect, request, Response, g
from flask.ext.cache import Cache 

import time
import urllib2
import xml.etree.ElementTree as ET


################
##### Configs ##
################
BASE_API_URL = "http://webservices.nextbus.com/service/publicXMLFeed"

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'simple'
app.cache = Cache(app)


###############################
##### Application API routes ##
###############################

@app.before_request
def before_request():
	g.start = time.time()

@app.teardown_request
def teardown_request(exceptions=None):
	diff = time.time() - g.start
	print "'%s', was the time spent to process the URL '%s'" % (diff, request.url)

@app.route('/service/publicXMLFeed')
def publicXMLFeed():
	

	#TODO: filter query params to redirect to the extended endpoints, or to just __proxy_pass
	if request.args.get('command') == 'notRunningRoutes':
		"""
		Use the extended method to process the command notRunningRoutes
		"""

		# Controller parameters validation 
		if not request.args.get('hour'):
			raise Exception("Invalid parameter 'hour'")

		try:
			requested_hour = int(request.args.get('hour'))
			
			if not 0 <= requested_hour < 24:
				raise Exception("ERROR: parameter 'hour' must be between 0 and 23")

		except ValueError:
			raise Exception("The hour value '%s' must be an integer between '0' and '23'." % request.args.get('hour'))

		agency = request.args.get('a')
		# Process
		min_epochtime, max_epochtime = __get_hour_limits_in_timestamp(requested_hour)
		xml_tree = __not_running_routes(agency, min_epochtime, max_epochtime)
		return Response(response=ET.tostring(xml_tree), status=200, mimetype='text/xml')

	""" 
	Apply a redirect to the original API
	"""
	query_strings = "?" + request.query_string if request.query_string else ""
	url = "%s%s" % (BASE_API_URL, query_strings)
	return __proxy_pass(url)


#########################
##### Useful functions ##
#########################


"""
Proxy pass requests to the 'BASE_API_URL'
"""
@app.cache.memoize(timeout=30)
def __proxy_pass(url):
	
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	return Response(response=response.read(), status=response.getcode(), mimetype=response.info().type)

"""
Converts an integer/hour value into milliseconds, that represents an hour, 
"""
def __get_hour_limits_in_timestamp(hour):
		
	min_epochtime = int(hour) * 60 * 60 * 1000
	max_epochtime = min_epochtime + (1 * 60 * 60 * 999)
	return min_epochtime, max_epochtime

#######################
##### Helper methods ##
#######################


"""
An endpoint to retrieve the routes that are not running at a specific time. 
For example, the 6 bus does not run between 1 AM and 5 AM, 
so the output of a query for 2 AM should include the 6.
"""
@app.cache.memoize(timeout=5*60)
def __not_running_routes(agency, min_epochtime, max_epochtime):

	# Check schedules for all routes:

	url = "http://webservices.nextbus.com/service/publicXMLFeed?command=routeList&a=%s" % agency
	req = urllib2.Request(url)
	content = urllib2.urlopen(req).read()

	xml_tree = ET.fromstring(content)
	xml_element_routes = xml_tree.getchildren()


	# Remove the routes that are running in that specific time
	#TODO remove this '[:2]' from the line below
	for i in xml_element_routes:
		if is_route_running_at_time(agency, i.attrib['tag'], min_epochtime, max_epochtime):
			xml_tree.remove(i)

	return xml_tree

@app.cache.memoize(timeout=5*60)
def __get_schedule_for_route(agency, route_tag):
	url = "http://webservices.nextbus.com/service/publicXMLFeed?command=schedule&a=sf-muni&r=%s" % route_tag
	print "Requesting URL: %s" % url
	
	req = urllib2.Request(url)
	content = urllib2.urlopen(req).read()
	return content

@app.cache.memoize(timeout=5*60)
def is_route_running_at_time(agency, route_tag, epoch_time_start, time_range_end):

	content = __get_schedule_for_route(agency, route_tag)

	xml_tree = ET.fromstring(content)
	for i in xml_tree.iter():
		if 'epochTime' in i.attrib and ( epoch_time_start <= int(i.attrib['epochTime']) <= time_range_end ):
				return True
	
	return False


if __name__ == '__main__':
	app.run(debug=True)
