from flask import Flask, request, Response, g, jsonify

import json
import sets
import urllib2
import xml.etree.ElementTree as ET


class NextbusApiExtension:

	def __init__(self, base_api_url='http://webservices.nextbus.com/service/publicXMLFeed', ):
		self.NEXTBUS_API_BASE_URL = base_api_url

		# A dictionary to store each route
		self.route_dict = {}

		# A dictionary to store each route schedule
		self.route_schedule_dict = {}

		self.epochtime_keys = map(lambda x: self.__hourToEpoch(x), range(0,23))


	"""
	Proxy pass requests to the NEXTBUS_API_BASE_URL'
	"""
	def proxy_pass(self, request_path):
		
		req = urllib2.Request(self.NEXTBUS_API_BASE_URL + request_path)
		response = urllib2.urlopen(req)
		return Response(response=response.read(), status=response.getcode(), mimetype=response.info().type)

	def get_routeList(self, agency):

		if agency in self.route_dict:
			return self.route_dict[agency]

		url = "%s?command=routeList&a=%s" % (self.NEXTBUS_API_BASE_URL, agency)
		print("Getting route list through request: '%s'" % url)
		req = urllib2.Request(url)
		content = urllib2.urlopen(req).read()
		print("Response :'%s'" % content)

		#return ET.fromstring(content)
		xml_tree = ET.fromstring(content)

		route_list = []
		for i in xml_tree:
			route_list.append(i.attrib)

		self.route_dict[agency] = route_list
		return route_list

	#@app.cache.memoize(timeout=30*60) # cached by 30 minutes
	def get_schedule_for_route(self, agency, route_tag):
		"""
			Returns a set data structure, containing the hours in which the route is running.
		"""

		agency_route_key = '%s_%s' % (agency, route_tag)

		# Check if value is already in dict
		if agency_route_key in self.route_schedule_dict:
			return self.route_schedule_dict[agency_route_key]

		# Requests on API
		url = "%s?command=schedule&a=%s&r=%s" % (self.NEXTBUS_API_BASE_URL, agency, route_tag)
		print("Requesting schedule for [agency: '%s', route_tag:'%s', url: '%s']" % (agency, route_tag, url))
		req = urllib2.Request(url)
		content = urllib2.urlopen(req).read()
		xml_tree = ET.fromstring(content)

		route_schedule_set = self.__convert_schedule_xml_object_to_set(xml_tree)
		
		# Put data in dictionary
		self.route_schedule_dict[agency_route_key] = route_schedule_set
		return route_schedule_set
	

	def __convert_schedule_xml_object_to_set(self, xml_tree):
		"""
			Converts a schedule response XML in a structured set containing each hour a route_tag is running
		"""

		agency_route_schedule = sets.Set()
		
		for i in xml_tree.iter():
			if not 'epochTime' in i.attrib:
				continue
			
			epochTime = int(i.attrib['epochTime'])

			for j in self.epochtime_keys[::-1]:

				if j in agency_route_schedule:
					continue

				## Check epochTimeRange
				if epochTime > j:
					agency_route_schedule.add(j)
					break

		return map(lambda x: self.__epochToHour(x), agency_route_schedule)


	def __hourToEpoch(self, int_hour):
		return int_hour * 60 * 60 * 1000

	def __epochToHour(self, int_epochtime):
		return int_epochtime / 60 / 60 / 1000