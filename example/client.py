#!/usr/bin/env python

from mt_data_api import DataAPI


def success(args1, args2=None):
    print(args1)
    if args2:
        print(args2)


def failure(error):
    print(error)


client = DataAPI()
client.api_base_url = 'http://localhost:5000/mt-data-api.cgi'
client.endpoint_version = 'v2'

client.authentication('admin', 'password', remember=False,
                      success=success, failure=failure)

client.endpoints(success, failure)

client.list_sites(success=success, failure=failure)
client.get_site(site_id=1, success=success, failure=failure)

entry = {
    'title': 'test123'
}
client.create_entry(site_id=1, entry=entry, success=success, failure=failure)
client.get_entry(site_id=1, entry_id=1, success=success, failure=failure)
entry = {
    'title': 'updated'
}
client.update_entry(site_id=1, entry_id=2, entry=entry,
                    success=success, failure=failure)
client.delete_entry(site_id=1, entry_id=2, success=success, failure=failure)
