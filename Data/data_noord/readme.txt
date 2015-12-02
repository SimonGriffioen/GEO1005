Public transport network of the Netherlands data set

author: Jorge Gil
date: 2012
licence: Creative Commons Attribution 3.0 ( CC BY 3.0 )  

description:
Public transport network of the Netherlands, including rail, metro, tram, bus/coach, and ferry links. The layers can be separated by mode. Bus and coach services are not distinguishable.
This is a simplified topological network for connectivity and general regional accessibility analysis. Stops on the same location and of the same mode have been aggregated into a single stop. It does not include realistic link distances or times between stops, link directions, individual service routes or times. The data is complete for the Randstad region and has connections to the Netherlands, but there may be bus stops and links missing in some other Provinces.
They include a "name match" column that allows the creation of transfers between modes.
The data is distributed as shape files, in the EPSG:28992 Amersfoort RD/New coordinate system. 

files and attributes:
transit_stops.shp
* sid - unique stop id
* stopname - name of the stop
* townname - name of the locality
* matchname - standardized name of the stop for all modes
* network - public transport mode
* buurtname - name of the neighbourhood
* gemeentename - name of the municipality

transit_links.shp
* sid 			- unique link id
* length		- metric length of the link, not the physical track
* azimuth		- angular direction of the link
* start_id		- id of the from transit stop
* end_id		- id of the to transit stop
* start_name 	- name of the from stop
* end_name		- name of the to stop
* network		- public transport mode
* temporal		- temporal distance of the link, based on an average speed of each mode