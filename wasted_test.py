#!/usr/bin/python

import json
import certifi
import logging
import re
from datetime import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Q,A, Search
from indexpattern import indexpattern_generate



client = Elasticsearch(['localhost:9200'], timeout = 60)

#TEMPORARY
#vo = 'uboone'
#wildcardVOq = '*'+vo+'*'
start_time = '2016/07/04'
end_time = '2016/07/05'


wildcardProbeNameq = 'condor:fifebatch?.fnal.gov'

start_date = re.split('[/ :]', start_time)
starttimeq = datetime(*[int(elt) for elt in start_date]).isoformat()

end_date = re.split('[/ :]', end_time)
endtimeq = datetime(*[int(elt) for elt in end_date]).isoformat()

s = Search(using = client, index = indexpattern_generate(start_date, end_date))\
           .query("wildcard",ProbeName=wildcardProbeNameq)\
	   .filter("range",EndTime={"gte":starttimeq,"lt":endtimeq})



#now do aggs
a1 = A('filters', filters = {'Success':{'bool':{'must':{'term':{'Resource_ExitCode':0}}}}, 
	'Failure': {'bool':{'must_not':{'term':{'Resource_ExitCode':0}}}}})
a5test = A('filters',other_bucket_key = 'Failure', filters = {'Success':{'term':{'Resource_ExitCode':0}}})


Buckets = s.aggs\
		.bucket('testbucket',a5test)

# FIGURE OUT HOW TO TOTAL JOBS
Metric = Buckets.metric('numJobs', 'value_count', field = 'GlobalJobId')\

response = s.execute()
resultset = response.aggregations

#print json.dumps(response.to_dict(),sort_keys=True,indent=4)

print resultset

for key in resultset.testbucket.buckets:
	print key, resultset.testbucket.buckets[key].numJobs.value

#for status in resultset.group_status:
#	print status
#	print status.group_VO.buckets
	#for VO in status.group_VO.buckets:
	#	for CommonName in VO.group_CommonName.buckets:
	##		print CommonName
##Temporary
#start_time ='2016/07/04 00:00'
#end_time='2016/07/05 23:59'
#
#
#
#
#
#
#s = Search(using = client,index = indexpattern_generate(start_date,end_date))\
#           .query("wildcard",VOName=wildcardVOq)\
#           .filter("range",EndTime={"gte":starttimeq,"lt":endtimeq})\
#           .filter(Q({"range":{"WallDuration":{"gt":0}}}))\
#           .filter(Q({"term":{"Host_description":"GPGrid"}}))\
#           .filter(Q({"term":{"ResourceType":"Payload"}}))\
#           [0:0]       #Size 0 to return only aggregations
#   
#Bucket = s.aggs.bucket('group_VOname','terms',field='ReportableVOName')\
#        .bucket('group_HostDescription','terms',field='Host_description')\
#        .bucket('group_commonName','terms',field='CommonName')
#
#Metric = Bucket.metric('Process_times_WallDur','sum',script="(doc['WallDuration'].value*doc['Processors'].value)")\
#                .metric('WallHours','sum',script="(doc['WallDuration'].value*doc['Processors'].value)/3600")\
#                .metric('CPUDuration','sum',field='CpuDuration')


