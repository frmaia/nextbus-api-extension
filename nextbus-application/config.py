DEBUG = True

###
## Redis Configuration
#
BASE_API_URL = "http://webservices.nextbus.com/service/publicXMLFeed"
REDIS_SERVER_HOST = 'redis'
REDIS_SERVER_PORT = 6379
REDIS_SERVER_PASSWORD = None

### 
## Application Cache configuration
#
#app.config['CACHE_TYPE'] = 'simple'
CACHE_TYPE = 'redis'
CACHE_REDIS_HOST = REDIS_SERVER_HOST
CACHE_REDIS_PORT = REDIS_SERVER_PORT
CACHE_REDIS_PASSWORD = REDIS_SERVER_PASSWORD

###
## Application business logic parameters
#
# Nextbus base API URL address. 
# For more info, refer to: http://www.nextbus.com/xmlFeedDocs/NextBusXMLFeed.pdf
NEXTBUS_API_BASE_URL = "http://webservices.nextbus.com/service/publicXMLFeed"

# Max response threshold (in seconds) for slow requests in API
SLOW_REQUEST_THRESHOLD = 2 

