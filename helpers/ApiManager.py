import datetime
import pickle

class ApiManager:

	SLOW_REQUEST_THRESHOLD = 2 # in seconds

	def __init__(self, redis_client):
		self.redis_c = redis_client
		

	def save_slow_request(self, url, time):
		request_datetime = datetime.datetime.fromtimestamp(int(self.redis_c.time()[0])).strftime('%Y-%m-%d %H:%M:%S')
		d = {"url": url, "request_date": request_datetime, "performance_in_seconds": time}
		self.redis_c.lpush('slow_requests', pickle.dumps(d))

	def incr_endpoint_count(self, endpoint):
		self.redis_c.incr('req_count___%s' % endpoint)

	def get_slow_requests(self):
		slow_requests = []
		for d in self.redis_c.lrange('slow_requests', 0, -1):
			slow_requests.append(pickle.loads(d))

		return slow_requests

	def get_total_number_of_queries(self):
		endpoints_counter = []
		for k in self.redis_c.keys('req_count*'):
			endpoint = k.split('___')[1:]
			d = { 'endpoint': endpoint, 'count': self.redis_c.get(k)}
			endpoints_counter.append(d)

		return endpoints_counter

