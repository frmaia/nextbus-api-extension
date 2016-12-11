#!/usr/bin/python

from flask import Flask, redirect, request, Response, g, jsonify
from flask.ext.cache import Cache 

import datetime
import json
import redis
import time
import urllib2
import xml.etree.ElementTree as ET
import pickle

################
##### Configs ##
################

app = Flask(__name__)

### GLOBAL VARS
BASE_API_URL = "http://webservices.nextbus.com/service/publicXMLFeed"
REDIS_SERVER_HOST = 'localhost'
REDIS_SERVER_PORT = 6379
REDIS_SERVER_PASSWORD = None

### Cache configuration
#app.config['CACHE_TYPE'] = 'simple'

app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_HOST'] = REDIS_SERVER_HOST
app.config['CACHE_REDIS_PORT'] = REDIS_SERVER_PORT
app.config['CACHE_REDIS_PASSWORD'] = REDIS_SERVER_PASSWORD

app.cache = Cache(app)

redis_c = redis.Redis(host=REDIS_SERVER_HOST, port=REDIS_SERVER_PORT, password=REDIS_SERVER_PASSWORD)


###############################
##### Application API routes ##
###############################


### Request handlers
@app.before_request
def before_request():
	g.start = time.time()

@app.teardown_request
def teardown_request(exceptions=None):
	processing_time = time.time() - g.start
	print "'%s', was the time spent to process the URL '%s'" % (processing_time, request.url)
	if processing_time > 2:
		__save_slow_request(request.url, processing_time)

	print "FULL PATH = %s" % request.full_path
	__incr_endpoint_count(request.full_path)



### Statistics - Slow Requests

def __save_slow_request(url, time):
	request_datetime = datetime.datetime.fromtimestamp(int(redis_c.time()[0])).strftime('%Y-%m-%d %H:%M:%S')
	d = {"url": url, "request_date": request_datetime, "performance_in_seconds": time}
	redis_c.lpush('slow_requests', pickle.dumps(d))

@app.route('/service/stats/slowRequests')
def get_slow_requests():
	slow_requests = []
	for d in redis_c.lrange('slow_requests', 0, -1):
		slow_requests.append(pickle.loads(d))

	return jsonify(slow_requests)



### Statistics - Endpoints

def __incr_endpoint_count(endpoint):
	redis_c.incr('req_count___%s' % endpoint)

@app.route('/service/stats/endpoints')
def get_total_number_of_queries():
	endpoints_counter = []
	for k in redis_c.keys('req_count*'):
		endpoint = k.split('___')[1:]
		d = { 'endpoint': endpoint, 'count': redis_c.get(k)}
		endpoints_counter.append(d)

	return jsonify(endpoints_counter)




### publicXMLFeed

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
#@app.cache.memoize(timeout=5*60)
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
		if __is_route_running_at_time(agency, i.attrib['tag'], min_epochtime, max_epochtime):
			xml_tree.remove(i)

	return xml_tree

@app.cache.memoize(timeout=30*60)
def __get_schedule_for_route(agency, route_tag):
	url = "http://webservices.nextbus.com/service/publicXMLFeed?command=schedule&a=%s&r=%s" % (agency, route_tag)
	print "Requesting URL: %s" % url
	
	req = urllib2.Request(url)
	content = urllib2.urlopen(req).read()
	return content

@app.cache.memoize(timeout=5*60)
def __is_route_running_at_time(agency, route_tag, epoch_time_start, time_range_end):

	content = __get_schedule_for_route(agency, route_tag)

	xml_tree = ET.fromstring(content)
	for i in xml_tree.iter():
		if 'epochTime' in i.attrib and ( epoch_time_start <= int(i.attrib['epochTime']) <= time_range_end ):
				return True
	
	return False


if __name__ == '__main__':
	app.run(debug=True)
