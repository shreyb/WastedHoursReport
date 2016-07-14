#!/usr/bin/python

import json
import certifi
import logging
import re
from datetime import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Q,A, Search
from indexpattern import indexpattern_generate


#client=Elasticsearch(['https://gracc.opensciencegrid.org/e'],
#                     use_ssl = True,
#                     verify_certs = True,
#                     ca_certs = certifi.where(),
#                     client_cert = 'gracc_cert/gracc-reports-dev.crt',
#                     client_key = 'gracc_cert/gracc-reports-dev.key',
#                     timeout = 60) 


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
a1 = A('filters', filters = {'Success':{'term':{'Resource_ExitCode':0}}, 
	'Failure': {'bool':{'must_not':{'term':{'Resource_ExitCode':0}}}}})
a2 = A('terms', field = 'VOName')
a3 = A('terms', field = 'CommonName')

Buckets = s.aggs\
		.bucket('group_VO',a2)\
		.bucket('group_CommonName',a3)
		
		#.bucket('group_status',a1)

# FIGURE OUT HOW TO TOTAL JOBS
Metric = Buckets.metric('numJobs', 'value_count', field = 'GlobalJobId')\
	.metric('WallHours','sum',script="(doc['WallDuration'].value*doc['Processors'].value/3600)")

response = s.execute()
resultset = response.aggregations


#print json.dumps(response.to_dict(),sort_keys=True,indent=4)

print resultset

for VO in resultset.group_VO.buckets:
	for CN in VO.group_CommonName.buckets:
		print VO.key, CN.key, CN.numJobs.value, CN.WallHours.value 

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


