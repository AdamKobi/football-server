from datetime import datetime
import requests
import os
import json

class GPSSportCrawler:
	def __init__(self, params, logger, days_to_download):
		self.params = params
		self.logger = logger
		self.days_to_download = days_to_download
		self.session = requests.Session()
		self.data = []

	def download(self):
		self.logger.info('Logging in to site')
		self.login()
		return(self.list_calendar())
		

	def login(self):
		url = 'http://eucloud.gpsports.com/auth/login'
		payload = {'username': self.params['gps_crawler']['user'], 'password': self.params['gps_crawler']['passwd']}
		r = self.session.post(url, data=json.dumps(payload))
		if r.status_code != 200:
			raise IOError('Error getting ' + url + ': ' + str(r.status_code) + ', ' + r.reason)

	def list_calendar(self):
		days_to_download = self.days_to_download
		session_list = []
		url = 'http://eucloud.gpsports.com/timeline/new/calendar'
		r = self.session.post(url, data=json.dumps({}))
		if r.status_code != 200:
			raise IOError('Error getting ' + url + ': ' + str(r.status_code) + ', ' + r.reason)
		response = json.loads(r.content)
		this_year = response[0]
		this_month = this_year['months'][0]
		session_days = this_month['days']
		for session_day in session_days[ : days_to_download]:
			activities = session_day['activities']
			day = session_day['id']
			self.logger.info(day + ': ' + str(len(activities)) + ' activities')
			for activity in activities:
				id = activity['id']
				name = activity['name']
				data = self.download_session(day+' ' + name, id)
				session_list.append(data)
		return (session_list)

	def download_session(self, name, id):

		url = 'http://eucloud.gpsports.com/report/ctr/'+id
		payload = {'fillBlankFieldsWith':0,
				'appendCustomParameters':0,
				'appendTags':1,
				'useAMS':1,
				'parameter_group_id[0]':'b8b74d47-5946-400f-882b-846433c5dd4d',
				'parameter_group_id[1]':'0b1a5cc2-72c8-4d41-9bce-b0ab873ced0d',
				'parameter_group_id[2]':'e53549c8-558b-4721-9887-d44d3acc38e6',
				'parameter_group_id[3]':'8a49529b-0fc6-46ab-a23e-78dcd3e69181',
				'parameter_group_id[4]':'01ff271e-99d9-40d7-9a35-8cc103b0ba48'}
		r = self.session.post(url, data=payload)
		if r.status_code != 200:
			raise IOError('Error getting ' + url + ': ' + str(r.status_code) + ', ' + r.reason)
		clean_name = ''.join(c for c in name if c not in '\/:*?<>|')
		self.logger.info('saving ' + clean_name)
		return(r.content)

