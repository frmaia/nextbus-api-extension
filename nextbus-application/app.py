#!/usr/bin/python

from flask import Flask, request, Response, g, jsonify
from flask_cache import Cache
from helpers.ApiManager import ApiManager
from models.NextbusApiExtension import NextbusApiExtension

import redis
import time

################
##### Configs ##
################

app = Flask(__name__)
app.config.from_object('config')
app.cache = Cache(app)

redis_c = redis.Redis(host=app.config['REDIS_SERVER_HOST'], port=app.config['REDIS_SERVER_PORT'], password=app.config['REDIS_SERVER_PASSWORD'])
api_manager = ApiManager(redis_client=redis_c)

nextbusApi = NextbusApiExtension(base_api_url=app.config['BASE_API_URL'])


schedule_dict = {}
###############################
##### Application API routes ##
###############################

### Request handlers

@app.before_request
def before_request():
	g.start = time.time()
	api_manager.incr_endpoint_count(request.full_path)


@app.teardown_request
def teardown_request(exceptions=None):
	processing_time = time.time() - g.start
	if processing_time > app.config['SLOW_REQUEST_THRESHOLD']:
		app.logger.warn("'%s', was the time spent to process the URL '%s'" % (processing_time, request.url))
		api_manager.save_slow_request(request.url, processing_time)

### Routes

###########################
### App Caching helpers ###
###########################

@app.cache.memoize(timeout=3*60) # cache by 30 minutes
def caching_proxy_pass(self, url):
	return nextbusApi.proxy_pass(url)

@app.cache.memoize(timeout=60*60) # cache by 1 hour
def caching_get_routeList(agency):
	return nextbusApi.get_routeList(agency)

@app.cache.memoize(timeout=60*60) # cache by 1 hour
def caching_get_schedule_for_route(agency, route_tag):
	return nextbusApi.get_schedule_for_route(agency, route_tag)

##############
### Routes ###
##############

@app.route('/service/stats/slowRequests')
def get_slow_requests():
	slow_requests = api_manager.get_slow_requests() 
	return jsonify(slow_requests)

@app.route('/service/stats/endpoints')
def get_total_number_of_queries():
	endpoints_counter = api_manager.get_total_number_of_queries()
	return jsonify(endpoints_counter)

@app.route('/service/publicXMLFeed')
def publicXMLFeed():
	
	if request.args.get('command') == 'notRunningRoutes':
		"""
		Use the extended method to process the command 'notRunningRoutes'
		"""
		#####
		##### Controller parameters validation 
		#####
		error_dict = None
		if not request.args.get('hour'):
			error_dict = {"error": "You must pass the 'hour' parameter as an integer value between '0' and '23'", "request": request.full_path}

		try:
			requested_hour = int(request.args.get('hour'))
			
			if not 0 <= requested_hour < 24:
				error_dict = {"error": "ERROR: parameter 'hour' must exists, and be between 0 and 23", "request": request.full_path}

		except ValueError:
			error_dict = {"error": "The 'hour' value '%s' must be an integer between '0' and '23'.", "request": request.full_path}
			
		if error_dict:
			app.logger.error(error_dict)
			return jsonify(error_dict)


		agency = request.args.get('a')
		
		#####
		##### Check not running routes for the specified agency
		#####
		not_running_routes = __get_not_running_routes(agency, requested_hour)
		return jsonify(not_running_routes)


	###
	### Apply a redirect to the original API
	###
	query_strings = "?" + request.query_string if request.query_string else ""
	return nextbusApi.proxy_pass(query_strings)


#######################
##### Helper methods ##
#######################

@app.cache.memoize(timeout=5*60) # cached for 5 minutes
def __get_not_running_routes(agency, int_hour):

	# Check schedules for all routes:
	route_list = caching_get_routeList(agency)

	not_running_routes = []
	for i in route_list:
		
		route_tag = i['tag']
		if not int_hour in caching_get_schedule_for_route(agency, route_tag):
			not_running_routes.append(i)

	return not_running_routes

def initcache():
	app.logger.info("Initiating cache!")
	
	agency='sf-muni'
	app.logger.info("Chaching routes for agency '%s'" % agency)
	for i in caching_get_routeList(agency):
		route_tag = i['tag']
		caching_get_schedule_for_route(agency, route_tag)

def thread_initcache():
	import threading
	t = threading.Thread(name='worker', target=initcache)
	t.start()

if __name__ == '__main__':
	#thread_initcache()
	app.run(debug=True, threaded=True, host='0.0.0.0')

