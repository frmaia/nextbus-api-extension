# nextbus-api-extension
### Project Description
This is a small project that extends the [NextBus API](http://www.nextbus.com/xmlFeedDocs/NextBusXMLFeed.pdf). In addition to doing a proxy pass to the endpoints officially documented, the following endpoints are implemented through this extension.

#### Query string 'command' extensions:
- /service/publicXMLFeed?command=**notRunningRoutes**&**hour**`<from 0 to 23`>&a=`<agency tag`> 
  - Query string command: 'notRunningRoutes', combined with 'hour', will return a list of all routes that haven't any scheduled run at that whole hour.

##### Requests examples:
- http://localhost/service/publicXMLFeed?command=notRunningRoutes&a=sf-muni&hour=20
- http://localhost/service/publicXMLFeed?command=notRunningRoutes&a=sf-muni&hour=3

#### New Endpoints:
- **/service/stats/endpoints**
  - Returns a JSON with the total number of queries made to each of the endpoints in this API.
- **/service/stats/slowRequests**
  - Returns a list of requests which response time exceeds the value SLOW_REQUEST_THRESHOLD (in seconds), specified in [config.py](./config.py).

##### Requests examples:
- http://localhost/service/stats/endpoints
- http://localhost/service/stats/slowRequests


## Architecture
- ```docker``` is used for infrastructure provisioning
- ```haproxy``` is used for Load Balancing
- ```python/flask``` is the framework used to build the web application
- ```redis``` is an in memory database, used for application cache and for storing some data-structures used by the [API Manager](./nextbus-application/helpers/ApiManager.py)

```

            +---------------+
            |               |
      +-----+    HAPROXY    +------+
      |     |               |      |
      |     +-------+-------+      |
      |             |              |
      |             |              |
      |             |              |
+-----+-------------+--------------+----+
|                                       |
|  Scaled   +-----+  +-----+  +-----+   |
|           |     |  |     |  |     |   |
|   Web     | WEB |  | WEB |  | WEB |   |
|           |     |  |     |  |     |   |
| Services  +-----+  +-----+  +-----+   |
|                                       |
+-----+--------+--------+----------+----+
      |        |        |          |
      |        |        |          |
      |        |        |          |
      |      +-+--------+---+      |
      |      |              |      |
      +------+     REDIS    +------+
             |              |
             +--------------+

```


### Run:
```bash
docker-compose build
docker-compose up 
```

#### Scale up / scale down
Use the command 'docker-compose scale' for scaling up or scaling down the web servers 
```bash
# -- Scale UP
$ docker-compose scale web=5 && docker exec nextbusapiextension_lb_1 /reload.sh
# -- Scale DOWN
$ docker-compose scale web=1 && docker exec nextbusapiextension_lb_1 /reload.sh
```
### TODO
- Apply better error handling --> http://flask.pocoo.org/docs/0.11/errorhandling/
- build unit and integration tests
- improve logging --> http://flask.pocoo.org/docs/0.11/errorhandling/
