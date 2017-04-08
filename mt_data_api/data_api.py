# The MIT License (MIT)
#
# Copyright (c) 2015 Six Apart, Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
from mt_data_api.basic_auth import BasicAuth
from mt_data_api.http_method import HTTPMethod
import re
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse


def stub_callback(*_):
    pass


class DataAPI(object):
    def __init__(self):
        self.__token = ""
        self.__session_id = ""
        self.endpoint_version = "v3"
        self.api_base_url = "http://localhost/cgi-bin/MT-6.1/mt-data-api.cgi"
        self.__api_version = ""
        self.client_id = "mt-data-api-sdk-python"
        self.basic_auth = BasicAuth()

    def __api_url(self):
        return self.api_base_url + '/' + self.endpoint_version

    def __api_url_v2(self):
        return self.api_base_url + '/v2'

    @classmethod
    def __encode_url(cls, src):
        return urllib.parse.quote(src)

    @classmethod
    def __decode_url(cls, src):
        return urllib.parse.unquote(src)

    @classmethod
    def __error_json(cls):
        return {'code': '-1', 'message': "The operation couldn't be completed."}

    def reset_auth(self):
        self.__token = ''
        self.__session_id = ''

    def __send_request(self, method, url, params=None, use_session=False, success=stub_callback, failure=stub_callback):
        headers = {}
        if self.__token:
            headers['X-MT-Authorization'] = 'MTAuth accessToken=' + self.__token
        if use_session and self.__session_id:
            headers['X-MT-Authorization'] = 'MTAuth sessionId=' + \
                self.__session_id

        auth = None
        if self.basic_auth.is_set():
            auth = HTTPBasicAuth(self.basic_auth.username,
                                 self.basic_auth.password)

        response = None
        if method == HTTPMethod.GET:
            response = requests.get(url, params, auth=auth, headers=headers)
        elif method == HTTPMethod.POST:
            response = requests.post(url, params, auth=auth, headers=headers)
        elif method == HTTPMethod.PUT:
            response = requests.put(url, params, auth=auth, headers=headers)
        elif method == HTTPMethod.DELETE:
            response = requests.delete(url, auth=auth, headers=headers)

        if response and response.status_code == requests.codes.ok:
            success(response)
        else:
            failure(self.__class__.__error_json())

    def __fetch_list(self, url, params, success, failure):
        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            success(json_response.get('items'),
                    json_response.get('totalResults'))
        self.__send_request(HTTPMethod.GET, url, params,
                            success=override_success, failure=failure)

    def __action_common(self, action, url, params=None, success=stub_callback, failure=stub_callback):
        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            success(json_response)
        self.__send_request(action, url, params,
                            success=override_success, failure=failure)

    def __action(self, name, action, url, object_=None, options=None, success=stub_callback, failure=stub_callback):
        if not options:
            options = {}
        if object_:
            options[name] = json.dumps(object_)
        self.__action_common(action, url, options, success, failure)

    def __get(self, url, params=None, success=stub_callback, failure=stub_callback):
        self.__action_common(HTTPMethod.GET, url, params, success, failure)

    def __post(self, url, params=None, success=stub_callback, failure=stub_callback):
        self.__action_common(HTTPMethod.POST, url, params, success, failure)

    def __put(self, url, params=None, success=stub_callback, failure=stub_callback):
        self.__action_common(HTTPMethod.PUT, url, params, success, failure)

    def __delete(self, url, params=None, success=stub_callback, failure=stub_callback):
        self.__action_common(HTTPMethod.DELETE, url, params, success, failure)

    def __repeat_action(self, action, url, options=None, success=stub_callback, failure=stub_callback):
        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            if json_response.get('status', '') == 'Complete' or json_response.get('restIds'):
                success(response)
            else:
                next_url = response.headers.get('X-MT-Next-Phase-URL')
                if next_url:
                    next_url = self.__api_url() + '/' + next_url
                    self.__repeat_action(
                        action, next_url, options, success, failure)
                else:
                    failure(self.__error_json)
        self.__send_request(action, url, options,
                            success=override_success, failure=failure)

    def __upload(self, data, file_name, url, params=None, success=stub_callback, failure=stub_callback):
        headers = {}
        if self.__token:
            headers['X-MT-Authorization'] = 'MTAuth accessToken=' + self.__token
        files = {'file': (file_name, data)}
        auth = None
        if self.basic_auth.is_set():
            auth = HTTPBasicAuth(self.basic_auth.username,
                                 self.basic_auth.password)
        response = requests.post(
            url, params, files=files, auth=auth, headers=headers)
        if response and response.status_code == requests.codes.ok:
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            success(json_response)
        else:
            failure(self.__class__.__error_json())

    # MARK: - APIs
    # MARK: - # V2
    # MARK: - System
    def endpoints(self, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/endpoints'
        self.__fetch_list(url, params=None, success=success, failure=failure)

    # MARK: - Authentication
    def __authentication_common(self, url, username, password, remember, success, failure):
        self.reset_auth()
        params = {
            'username': username,
            'password': password,
            'remember': '1' if remember else '0',
            'clientId': self.client_id,
        }

        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            if json_response.get('accessToken'):
                self.__token = json_response.get('accessToken')
            if json_response.get('sessionID'):
                self.__session_id = json_response.get('sessionID')
            success(json_response)
        self.__send_request(HTTPMethod.POST, url, params,
                            success=override_success, failure=failure)

    def authentication(self, username, password, remember, success, failure):
        url = self.__api_url() + '/authentication'
        self.__authentication_common(
            url, username, password, remember, success, failure)

    def authentication_v2(self, username, password, remember, success, failure):
        url = self.__api_url_v2() + '/authentication'
        self.__authentication_common(
            url, username, password, remember, success, failure)

    def get_token(self, success, failure):
        if not self.__session_id:
            failure(self.__class__.__error_json())
            return
        url = self.__api_url() + '/token'

        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            if json_response.get('accessToken'):
                self.__token = json_response.get('accessToken')
            success(json_response)
        self.__send_request(HTTPMethod.POST, url, use_session=True,
                            success=override_success, failure=failure)

    def revoke_authentication(self, success, failure):
        if not self.__session_id:
            failure(self.__class__.__error_json())
            return
        url = self.__api_url() + '/authentication'

        def override_success(response):
            json_response = response.json()
            if json_response.get('error'):
                failure(json_response.get('error'))
                return
            self.__session_id = ''
            success(json_response)
        self.__send_request(HTTPMethod.DELETE, url,
                            success=override_success, failure=failure)

    def revoke_token(self, success, failure):
        url = self.__api_url() + '/token'

        def override_success(response):
            json_response = response.json()
            self.__token = ''
            success(json_response)
        self.__send_request(HTTPMethod.DELETE, url,
                            success=override_success, failure=failure)

    # MARK: - Search
    def search(self, query, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/search'
        if not options:
            options = {}
        options['search'] = query
        self.__fetch_list(url, options, success, failure)

    # MARK: - Site
    def list_sites(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites'
        self.__fetch_list(url, options, success, failure)

    def list_sites_by_parent(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/children' % site_id
        self.__fetch_list(url, options, success, failure)

    def __site_action(self, action, site_id, site, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites'
        if action != HTTPMethod.POST and site_id:
            url += '/' + str(site_id)
        self.__action('website', action, url, site, options, success, failure)

    def create_site(self, site, options=None, success=stub_callback, failure=stub_callback):
        self.__site_action(HTTPMethod.POST, site_id=None, site=site,
                           options=options, success=success, failure=failure)

    def get_site(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        self.__site_action(HTTPMethod.GET, site_id, site=None,
                           options=options, success=success, failure=failure)

    def update_site(self, site_id, site, options=None, success=stub_callback, failure=stub_callback):
        self.__site_action(HTTPMethod.PUT, site_id, site,
                           options, success, failure)

    def delete_site(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        self.__site_action(HTTPMethod.DELETE, site_id, site=None,
                           options=options, success=success, failure=failure)

    def backup_site(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/backup' % site_id
        self.__get(url, options, success, failure)

    # MARK: - Blog
    def list_blogs_for_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users/%s/sites' % user_id
        self.__fetch_list(url, options, success, failure)

    def __blog_action(self, action, blog_id, blog=None, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites'
        if blog_id:
            url += '/' + str(blog_id)
        self.__action('blog', action, url, blog, options, success, failure)

    def create_blog(self, blog, options=None, success=stub_callback, failure=stub_callback):
        self.__blog_action(HTTPMethod.POST, blog_id=None, blog=blog,
                           options=options, success=success, failure=failure)

    def get_blog(self, blog_id, options=None, success=stub_callback, failure=stub_callback):
        self.__blog_action(HTTPMethod.GET, blog_id, blog=None,
                           options=options, success=success, failure=failure)

    def update_blog(self, blog_id, blog, options=None, success=stub_callback, failure=stub_callback):
        self.__blog_action(HTTPMethod.PUT, blog_id, blog,
                           options, success, failure)

    def delete_blog(self, blog_id, options=None, success=stub_callback, failure=stub_callback):
        self.__blog_action(HTTPMethod.DELETE, blog_id, blog=None,
                           options=options, success=success, failure=failure)

    # MARK: - Entry
    def list_entries(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries' % site_id
        self.__fetch_list(url, options, success, failure)

    def __entry_action(self, action, site_id, entry_id=None, entry=None, options=None, success=stub_callback,
                       failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries' % site_id
        if action != HTTPMethod.POST and entry_id:
            url += '/' + str(entry_id)
        self.__action('entry', action, url, entry, options, success, failure)

    def create_entry(self, site_id, entry, options=None, success=stub_callback, failure=stub_callback):
        self.__entry_action(HTTPMethod.POST, site_id, entry_id=None,
                            entry=entry, options=options, success=success, failure=failure)

    def get_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        self.__entry_action(HTTPMethod.GET, site_id, entry_id, entry=None,
                            options=options, success=success, failure=failure)

    def update_entry(self, site_id, entry_id, entry, options=None, success=stub_callback, failure=stub_callback):
        self.__entry_action(HTTPMethod.PUT, site_id, entry_id,
                            entry, options, success, failure)

    def delete_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        self.__entry_action(HTTPMethod.DELETE, site_id, entry_id,
                            entry=None, options=options, success=success, failure=failure)

    def __list_entries_for_object(self, object_name, site_id, object_id, options=None, success=stub_callback,
                                  failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/entries' % (site_id, object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_entries_for_category(self, site_id, category_id, options=None, success=stub_callback,
                                  failure=stub_callback):
        self.__list_entries_for_object(object_name='categories', site_id=site_id,
                                       object_id=category_id, options=options, success=success, failure=failure)

    def list_entries_for_asset(self, site_id, asset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_entries_for_object(object_name='assets', site_id=site_id,
                                       object_id=asset_id, options=options, success=success, failure=failure)

    def list_entries_for_site_and_tag(self, site_id, tag_id, options=None, success=stub_callback,
                                      failure=stub_callback):
        self.__list_entries_for_object(object_name='tags', site_id=site_id,
                                       object_id=tag_id, options=options, success=success, failure=failure)

    def export_entries(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries/export' % site_id

        def override_success(response):
            if re.match(pattern='\{"error":', string=response.text):
                json_response = response.json()
                failure(json_response.get('error'))
                return
            success(response)
        self.__send_request(HTTPMethod.GET, url, options,
                            success=override_success, failure=failure)

    def publish_entries(self, entry_ids, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/publish/entries'
        if not options:
            options = {}
        options['ids'] = entry_ids.join(',')
        self.__repeat_action(HTTPMethod.GET, url, options, success, failure)

    def __import_entries_with_file(self, site_id, import_data, options=None, success=stub_callback,
                                   failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries/import' % site_id
        self.__upload(import_data, file_name='import.dat', url=url,
                      params=options, success=success, failure=failure)

    def import_entries(self, site_id, import_data=None, options=None, success=stub_callback, failure=stub_callback):
        if import_data:
            self.__import_entries_with_file(
                site_id, import_data, options, success, failure)
            return
        url = self.__api_url() + '/sites/%s/entries/import' % site_id
        self.__post(url, options, success, failure)

    def preview_entry(self, site_id, entry_id=None, entry=None, options=None, success=stub_callback,
                      failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries' % site_id
        if entry_id:
            url += '/%s/preview' % entry_id
        else:
            url += '/preview'
        self.__action('entry', HTTPMethod.POST, url,
                      entry, options, success, failure)

    # MARK: - Page
    def list_pages(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/pages' % site_id
        self.__fetch_list(url, options, success, failure)

    def __page_action(self, action, site_id, page_id=None, page=None, options=None, success=stub_callback,
                      failure=stub_callback):
        url = self.__api_url() + '/sites/%s/pages' % site_id
        if action != HTTPMethod.POST and page_id:
            url += '/' + str(page_id)
        self.__action('page', action, url, page, options, success, failure)

    def create_page(self, site_id, page, options=None, success=stub_callback, failure=stub_callback):
        self.__page_action(HTTPMethod.POST, site_id, page_id=None,
                           page=page, options=options, success=success, failure=failure)

    def get_page(self, site_id, page_id, options=None, success=stub_callback, failure=stub_callback):
        self.__page_action(HTTPMethod.GET, site_id, page_id, page=None,
                           options=options, success=success, failure=failure)

    def update_page(self, site_id, page_id, page, options=None, success=stub_callback, failure=stub_callback):
        self.__page_action(HTTPMethod.PUT, site_id, page_id,
                           page, options, success, failure)

    def delete_page(self, site_id, page_id, options=None, success=stub_callback, failure=stub_callback):
        self.__page_action(HTTPMethod.DELETE, site_id, page_id, page=None,
                           options=options, success=success, failure=failure)

    def __list_pages_for_object(self, object_name, site_id, object_id, options=None, success=stub_callback,
                                failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/pages' % (site_id, object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_pages_for_folder(self, site_id, folder_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_pages_for_object(
            'folders', site_id, folder_id, options, success, failure)

    def list_pages_for_asset(self, site_id, asset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_pages_for_object(
            'assets', site_id, asset_id, options, success, failure)

    def list_pages_for_site_and_tag(self, site_id, tag_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_pages_for_object(
            'tags', site_id, tag_id, options, success, failure)

    def preview_page(self, site_id, page_id=None, entry=None, options=None, success=stub_callback,
                     failure=stub_callback):
        url = self.__api_url() + '/sites/%s/pages' % site_id
        if page_id:
            url += '/%s/preview' % page_id
        else:
            url += '/preview'
        self.__action('page', HTTPMethod.POST, url,
                      entry, options, success, failure)

    # MARK: - Category
    def list_categories(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/categories' % site_id
        self.__fetch_list(url, options, success, failure)

    def __category_action(self, action, site_id, category_id=None, category=None, options=None, success=stub_callback,
                          failure=stub_callback):
        url = self.__api_url() + '/sites/%s/categories' % site_id
        if action != HTTPMethod.POST and category_id:
            url += '/' + str(category_id)
        self.__action('category', action, url, category,
                      options, success, failure)

    def create_category(self, site_id, category, options=None, success=stub_callback, failure=stub_callback):
        self.__category_action(HTTPMethod.POST, site_id, category_id=None,
                               category=category, options=options, success=success, failure=failure)

    def get_category(self, site_id, category_id, options=None, success=stub_callback, failure=stub_callback):
        self.__category_action(HTTPMethod.GET, site_id, category_id,
                               category=None, options=options, success=success, failure=failure)

    def update_category(self, site_id, category_id, category, options=None, success=stub_callback,
                        failure=stub_callback):
        self.__category_action(HTTPMethod.PUT, site_id,
                               category_id, category, options, success, failure)

    def delete_category(self, site_id, category_id, options=None, success=stub_callback, failure=stub_callback):
        self.__category_action(HTTPMethod.DELETE, site_id, category_id,
                               category=None, options=options, success=success, failure=failure)

    def list_categories_for_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/entries/%s/categories' % (site_id, entry_id)
        self.__fetch_list(url, options, success, failure)

    def __list_categories_for_relation(self, relation, site_id, category_id, options=None, success=stub_callback,
                                       failure=stub_callback):
        url = self.__api_url() + '/sites/%s/categories/%s/%s' % (site_id, category_id, relation)
        self.__fetch_list(url, options, success, failure)

    def list_parent_categories(self, site_id, category_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_categories_for_relation(
            'parents', site_id, category_id, options, success, failure)

    def list_sibling_categories(self, site_id, category_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_categories_for_relation(
            'siblings', site_id, category_id, options, success, failure)

    def list_child_categories(self, site_id, category_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_categories_for_relation(
            'children', site_id, category_id, options, success, failure)

    def permutate_categories(self, site_id, categories=None, options=None, success=stub_callback,
                             failure=stub_callback):
        url = self.__api_url() + '/sites/%s/categories/permutate' % site_id
        if not options:
            options = {}
        if categories:
            options['categories'] = json.dumps(categories)
        self.__post(url, options, success, failure)

    # MARK: - Folder
    def list_folders(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/folders' % site_id
        self.__fetch_list(url, options, success, failure)

    def __folder_action(self, action, site_id, folder_id=None, folder=None, options=None, success=stub_callback,
                        failure=stub_callback):
        url = self.__api_url() + '/sites/%s/folders' % site_id
        if folder_id:
            url += '/' + str(folder_id)
        self.__action('folder', action, url, folder, options, success, failure)

    def create_folder(self, site_id, folder, options=None, success=stub_callback, failure=stub_callback):
        self.__folder_action(HTTPMethod.POST, site_id, folder_id=None,
                             folder=folder, options=options, success=success, failure=failure)

    def get_folder(self, site_id, folder_id, options=None, success=stub_callback, failure=stub_callback):
        self.__folder_action(HTTPMethod.GET, site_id, folder_id, folder=None,
                             options=options, success=success, failure=failure)

    def update_folder(self, site_id, folder_id, folder, options=None, success=stub_callback, failure=stub_callback):
        self.__folder_action(HTTPMethod.PUT, site_id,
                             folder_id, folder, options, success, failure)

    def delete_folder(self, site_id, folder_id, options=None, succsss=stub_callback, failure=stub_callback):
        self.__folder_action(HTTPMethod.DELETE, site_id, folder_id,
                             folder=None, options=options, success=succsss, failure=failure)

    def __list_folder_for_relation(self, relation, site_id, folder_id, options=None, success=stub_callback,
                                   failure=stub_callback):
        url = self.__api_url() + '/sites/%s/folders/%s/%s' % (site_id, folder_id, relation)
        self.__fetch_list(url, options, success, failure)

    def list_parent_folders(self, site_id, folder_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_folder_for_relation(
            'parents', site_id, folder_id, options, success, failure)

    def list_sibling_folders(self, site_id, folder_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_folder_for_relation(
            'siblings', site_id, folder_id, options, success, failure)

    def list_child_folders(self, site_id, folder_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_folder_for_relation(
            'children', site_id, folder_id, options, success, failure)

    def permutate_folders(self, site_id, folders=None, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/folders/permutate' % site_id
        if not options:
            options = {}
        if folders:
            options['folders'] = json.dumps(folders)
        self.__post(url, options, success, failure)

    # MARK: - Tag
    def list_tags(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/tags' % site_id
        self.__fetch_list(url, options, success, failure)

    def __tag_action(self, action, site_id, tag_id, tag=None, options=None, success=stub_callback,
                     failure=stub_callback):
        if action == HTTPMethod.POST:
            failure(self.__error_json())
            return
        url = self.__api_url() + '/sites/%s/tags/%s' % (site_id, tag_id)
        self.__action('tag', action, url, tag, options, success, failure)

    def get_tag(self, site_id, tag_id, options=None, success=stub_callback, failure=stub_callback):
        self.__tag_action(HTTPMethod.GET, site_id, tag_id, tag=None,
                          options=options, success=success, failure=failure)

    def update_tag(self, site_id, tag_id, tag, options=None, success=stub_callback, failure=stub_callback):
        self.__tag_action(HTTPMethod.PUT, site_id, tag_id,
                          tag, options, success, failure)

    def delete_tag(self, site_id, tag_id, options=None, success=stub_callback, failure=stub_callback):
        self.__tag_action(HTTPMethod.DELETE, site_id, tag_id, tag=None,
                          options=options, success=success, failure=failure)

    # MARK: - User
    def list_users(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users'
        self.__fetch_list(url, options, success, failure)

    def __user_action(self, action, user_id=None, user=None, options=None, success=stub_callback,
                      failure=stub_callback):
        url = self.__api_url() + '/users'
        if action != HTTPMethod.POST and user_id:
            url += '/' + str(user_id)
        self.__user_action('user', url, user, options, success, failure)

    def create_user(self, user, options=None, success=stub_callback, failure=stub_callback):
        self.__user_action(HTTPMethod.POST, user_id=None, user=user,
                           options=options, success=success, failure=failure)

    def get_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        self.__user_action(HTTPMethod.GET, user_id, user=None,
                           options=options, success=success, failure=failure)

    def update_user(self, user_id, user, options=None, success=stub_callback, failure=stub_callback):
        self.__user_action(HTTPMethod.PUT, user_id, user,
                           options, success, failure)

    def delete_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        self.__user_action(HTTPMethod.DELETE, user_id, user=None,
                           options=options, success=success, failure=failure)

    def unlock_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users/%s/unlock' % user_id
        self.__post(url, options, success, failure)

    def recover_password_for_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users/%s/recover_password' % user_id
        self.__post(url, options, success, failure)

    def recover_password(self, name, email, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/recover_password'
        if not options:
            options = {}
        options['name'] = name
        options['email'] = email
        self.__post(url, options, success, failure)

    # MARK: - Asset
    def list_assets(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/assets' % site_id
        self.__fetch_list(url, options, success, failure)

    def upload_asset(self, asset_data, file_name, options=None, success=stub_callback, failure=stub_callback):
        self.upload_asset_for_site(site_id=None, asset_data=asset_data,
                                   file_name=file_name, options=options, success=success, failure=failure)

    def upload_asset_for_site(self, site_id, asset_data, file_name, options=None, success=stub_callback,
                              failure=stub_callback):
        url = self.__api_url()
        if site_id:
            url += '/sites/%s/assets/upload'
        else:
            url += '/assets/upload'
        self.__upload(asset_data, file_name, url, options, success, failure)

    def __asset_action(self, action, site_id, asset_id, asset=None, options=None, success=stub_callback,
                       failure=stub_callback):
        url = self.__api_url() + '/sites/%s/assets' % site_id
        if action != HTTPMethod.POST:
            url += '/' + str(asset_id)
        else:
            failure(self.__error_json())
            return
        self.__action('asset', action, url, asset, options, success, failure)

    def get_asset(self, site_id, asset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__asset_action(HTTPMethod.GET, site_id, asset_id, asset=None,
                            options=options, success=success, failure=failure)

    def update_asset(self, site_id, asset_id, asset, options=None, success=stub_callback, failure=stub_callback):
        self.__asset_action(HTTPMethod.PUT, site_id, asset_id,
                            asset, options, success, failure)

    def delete_asset(self, site_id, asset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__asset_action(HTTPMethod.DELETE, site_id, asset_id,
                            asset=None, options=options, success=success, failure=failure)

    def __list_assets_for_object(self, object_name, site_id, object_id, options=None, success=stub_callback,
                                 failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s' % (site_id, object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_assets_for_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_assets_for_object(
            'entries', site_id, entry_id, options, success, failure)

    def list_assets_for_page(self, site_id, page_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_assets_for_object(
            'pages', site_id, page_id, options, success, failure)

    def list_assets_for_site_and_tag(self, site_id, tag_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_assets_for_object(
            'tags', site_id, tag_id, options, success, failure)

    def get_thumbnail(self, site_id, asset_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/assets/%s/thumbnail' % (site_id, asset_id)
        self.__get(url, options, success, failure)

    # MARK: - Comment
    def list_comments(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/comments' % site_id
        self.__fetch_list(url, options, success, failure)

    def __comment_action(self, action, site_id, comment_id, comment=None, options=None, success=stub_callback,
                         failure=stub_callback):
        url = self.__api_url() + '/sites/%s/comments' % site_id
        if action != HTTPMethod.POST:
            url += '/' + str(comment_id)
        else:
            failure(self.__error_json())
            return
        self.__action('comment', action, url, comment,
                      options, success, failure)

    def get_comment(self, site_id, comment_id, options=None, success=stub_callback, failure=stub_callback):
        self.__comment_action(HTTPMethod.GET, site_id, comment_id,
                              comment=None, options=options, success=success, failure=failure)

    def update_comment(self, site_id, comment_id, comment, options=None, success=stub_callback, failure=stub_callback):
        self.__comment_action(HTTPMethod.PUT, site_id,
                              comment_id, comment, options, success, failure)

    def delete_comment(self, site_id, comment_id, options=None, success=stub_callback, failure=stub_callback):
        self.__comment_action(HTTPMethod.DELETE, site_id, comment_id,
                              comment=None, options=options, success=success, failure=failure)

    def __list_comments_for_object(self, object_name, site_id, object_id, options=None, success=stub_callback,
                                   failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/comments' % (site_id, object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_comments_for_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_comments_for_object(
            'entries', site_id, entry_id, options, success, failure)

    def list_comments_for_page(self, site_id, page_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_comments_for_object(
            'pages', site_id, page_id, options, success, failure)

    def __create_comment_for_object(self, object_name, site_id, object_id, comment, options=None, success=stub_callback,
                                    failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/comments' % (site_id, object_name, object_id)
        self.__action('comment', HTTPMethod.POST, url,
                      comment, options, success, failure)

    def create_comment_for_entry(self, site_id, entry_id, comment, options=None, success=stub_callback,
                                 failure=stub_callback):
        self.__create_comment_for_object(
            'entries', site_id, entry_id, comment, options, success, failure)

    def create_comment_for_page(self, site_id, page_id, comment, options=None, success=stub_callback,
                                failure=stub_callback):
        self.__create_comment_for_object(
            'pages', site_id, page_id, comment, options, success, failure)

    def __create_reply_comment_for_object(self, object_name, site_id, object_id, comment_id, reply, options=None,
                                          success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/comments/%s/replies' % (site_id,
                                                                          object_name, object_id, comment_id)
        self.__action('comment', HTTPMethod.POST, url,
                      reply, options, success, failure)

    def create_reply_comment_for_entry(self, site_id, entry_id, comment_id, reply, options=None, success=stub_callback,
                                       failure=stub_callback):
        self.__create_reply_comment_for_object(
            site_id, entry_id, comment_id, reply, options, success, failure)

    def create_reply_comment_for_page(self, site_id, page_id, comment_id, reply, options=None, success=stub_callback,
                                      failure=stub_callback):
        self.__create_reply_comment_for_object(
            site_id, page_id, comment_id, reply, options, success, failure)

    # MARK: - Trackback
    def list_trackbacks(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/trackbacks' % site_id
        self.__fetch_list(url, options, success, failure)

    def __trackback_action(self, action, site_id, trackback_id, trackback=None, options=None, success=stub_callback,
                           failure=stub_callback):
        url = self.__api_url() + '/sites/%s/trackbacks' % site_id
        if action != HTTPMethod.POST:
            url += '/' + str(trackback_id)
        else:
            failure(self.__error_json())
            return
        self.__action('trackback', action, url, trackback,
                      options, success, failure)

    def get_trackback(self, site_id, trackback_id, options=None, success=stub_callback, failure=stub_callback):
        self.__trackback_action(HTTPMethod.GET, site_id, trackback_id,
                                trackback=None, options=options, success=success, failure=failure)

    def update_trackback(self, site_id, trackback_id, trackback, options=None, success=stub_callback,
                         failure=stub_callback):
        self.__trackback_action(
            HTTPMethod.PUT, site_id, trackback_id, trackback, options, success, failure)

    def delete_trackback(self, site_id, trackback_id, options=None, success=stub_callback, failure=stub_callback):
        self.__trackback_action(HTTPMethod.DELETE, site_id, trackback_id,
                                trackback=None, options=options, success=success, failure=failure)

    def __list_trackbacks_for_object(self, object_name, site_id, object_id, options=None, success=stub_callback,
                                     failure=stub_callback):
        url = self.__api_url() + '/sites/%s/%s/%s/trackbacks' % (site_id, object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_trackbacks_for_entry(self, site_id, entry_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_trackbacks_for_object(
            'entries', site_id, entry_id, options, success, failure)

    def list_trackbacks_for_page(self, site_id, page_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_trackbacks_for_object(
            'pages', site_id, page_id, options, success, failure)

    # MARK: - Field
    def list_fields(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/fields' % site_id
        self.__fetch_list(url, options, success, failure)

    def __field_action(self, action, site_id, field_id, field=None, options=None, success=stub_callback,
                       failure=stub_callback):
        url = self.__api_url() + '/sites/%s/fields' % site_id
        if action != HTTPMethod.POST and field_id:
            url += '/' + str(field_id)
        self.__action('field', action, url, field, options, success, failure)

    def create_field(self, site_id, field, options=None, success=stub_callback, failure=stub_callback):
        self.__field_action(HTTPMethod.POST, site_id, field_id=None,
                            field=field, options=options, success=success, failure=failure)

    def get_field(self, site_id, field_id, options=None, success=stub_callback, failure=stub_callback):
        self.__field_action(HTTPMethod.GET, site_id, field_id, field=None,
                            options=options, success=success, failure=failure)

    def update_field(self, site_id, field_id, field, options=None, success=stub_callback, failure=stub_callback):
        self.__field_action(HTTPMethod.PUT, site_id, field_id,
                            field, options, success, failure)

    def delete_field(self, site_id, field_id, options=None, success=stub_callback, failure=stub_callback):
        self.__field_action(HTTPMethod.DELETE, site_id, field_id,
                            field=None, options=options, success=success, failure=failure)

    # MARK: - Template
    def list_templates(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates' % site_id
        self.__fetch_list(url, options, success, failure)

    def __template_action(self, action, site_id, template_id=None, template=None, options=None, success=stub_callback,
                          failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates' % site_id
        if action != HTTPMethod.POST and template_id:
            url += '/' + str(template_id)
        self.__action('template', action, url, template,
                      options, success, failure)

    def create_template(self, site_id, template, options=None, success=stub_callback, failure=stub_callback):
        self.__template_action(HTTPMethod.POST, site_id, template_id=None,
                               template=template, options=options, success=success, failure=failure)

    def get_template(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        self.__template_action(HTTPMethod.GET, site_id, template_id,
                               template=None, options=options, success=success, failure=failure)

    def update_template(self, site_id, template_id, template, options=None, success=stub_callback,
                        failure=stub_callback):
        self.__template_action(HTTPMethod.PUT, site_id,
                               template_id, template, options, success, failure)

    def delete_template(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        self.__template_action(HTTPMethod.DELETE, site_id, template_id,
                               template=None, options=options, success=success, failure=failure)

    def publish_template(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates/%s/publish' % (site_id, template_id)
        self.__post(url, options, success, failure)

    def refresh_template(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates/%s/refresh' % (site_id, template_id)
        self.__post(url, options, success, failure)

    def refresh_templates_for_site(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/refresh_templates' % site_id
        self.__post(url, options, success, failure)

    def clone_template(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates/%s/clone' % (site_id, template_id)
        self.__post(url, options, success, failure)

    # MARK: - TemplateMap
    def list_templatemaps(self, site_id, template_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates/%s/templatemaps' % (site_id, template_id)
        self.__fetch_list(url, options, success, failure)

    def __templatemap_action(self, action, site_id, template_id, templatemap_id=None, templatemap=None, options=None,
                             success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/templates/%s/templatemaps' % (site_id, template_id)
        if action != HTTPMethod.POST and templatemap_id:
            url += '/' + str(templatemap_id)
        self.__action('templatemap', action, url,
                      templatemap, options, success, failure)

    def create_templatemap(self, site_id, template_id, templatemap, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__templatemap_action(HTTPMethod.POST, site_id, template_id, templatemap_id=None,
                                  templatemap=templatemap, options=options, success=success, failure=failure)

    def get_templatemap(self, site_id, template_id, templatemap_id, options=None, success=stub_callback,
                        failure=stub_callback):
        self.__templatemap_action(HTTPMethod.GET, site_id, template_id, templatemap_id,
                                  templatemap=None, options=options, success=success, failure=failure)

    def update_templatemap(self, site_id, template_id, templatemap_id, templatemap, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__templatemap_action(HTTPMethod.PUT, site_id, template_id,
                                  templatemap_id, templatemap, options, success, failure)

    def delete_templatemap(self, site_id, template_id, templatemap_id, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__templatemap_action(HTTPMethod.DELETE, site_id, template_id, templatemap_id,
                                  templatemap=None, options=options, success=success, failure=failure)

    # MARK: - Widget
    def list_widgets(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgets' % site_id
        self.__fetch_list(url, options, success, failure)

    def list_widgets_for_widgetset(self, site_id, widgetset_id, options=None, success=stub_callback,
                                   failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgetsets/%s/widgets' % (site_id, widgetset_id)
        self.__fetch_list(url, options, success, failure)

    def get_widget_for_widgetset(self, site_id, widgetset_id, widget_id, options=None, success=stub_callback,
                                 failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgetsets/%s/widgets/%s' % (site_id,
                                                                         widgetset_id, widget_id)
        self.__action('widget', HTTPMethod.GET, url, options, success, failure)

    def __widget_action(self, action, site_id, widget_id=None, widget=None, options=None, success=stub_callback,
                        failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgets' % site_id
        if action != HTTPMethod.POST and widget_id:
            url += '/' + str(widget_id)
        self.__action('widget', action, url, widget, options, success, failure)

    def create_widget(self, site_id, widget, options=None, success=stub_callback, failure=stub_callback):
        self.__widget_action(HTTPMethod.POST, site_id, widget_id=None,
                             widget=widget, options=options, success=success, failure=failure)

    def get_widget(self, site_id, widget_id, options=None, success=stub_callback, failure=stub_callback):
        self.__widget_action(HTTPMethod.GET, site_id, widget_id, widget=None,
                             options=options, success=success, failure=failure)

    def update_widget(self, site_id, widget_id, widget, options=None, success=stub_callback, failure=stub_callback):
        self.__widget_action(HTTPMethod.PUT, site_id,
                             widget_id, widget, options, success, failure)

    def delete_widget(self, site_id, widget_id, options=None, success=stub_callback, failure=stub_callback):
        self.__widget_action(HTTPMethod.DELETE, site_id, widget_id,
                             widget=None, options=options, success=success, failure=failure)

    def refresh_widget(self, site_id, widget_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgets/%s/refresh' % (site_id, widget_id)
        self.__post(url, options, success, failure)

    def clone_widget(self, site_id, widget_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgets/%s/clone' % (site_id, widget_id)
        self.__post(url, options, success, failure)

    # MARK: - WidgetSet
    def list_widgetsets(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgetsets' % site_id
        self.__fetch_list(url, options, success, failure)

    def __widgetset_action(self, action, site_id, widgetset_id=None, widgetset=None, options=None,
                           success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/widgetsets' % site_id
        if action != HTTPMethod.POST and widgetset_id:
            url += '/' + str(widgetset_id)
        self.__action('widgetset', action, url, widgetset,
                      options, success, failure)

    def create_widgetset(self, site_id, widgetset, options=None, success=stub_callback, failure=stub_callback):
        self.__widgetset_action(HTTPMethod.POST, site_id, widgetset_id=None,
                                widgetset=widgetset, options=options, success=success, failure=failure)

    def get_widgetset(self, site_id, widgetset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__widget_action(HTTPMethod.GET, site_id, widgetset_id,
                             widget=None, options=options, success=success, failure=failure)

    def update_widgetset(self, site_id, widgetset_id, widgetset, options=None, success=stub_callback,
                         failure=stub_callback):
        self.__widgetset_action(
            HTTPMethod.PUT, site_id, widgetset_id, widgetset, options, success, failure)

    def delete_widgetset(self, site_id, widgetset_id, options=None, success=stub_callback, failure=stub_callback):
        self.__widgetset_action(HTTPMethod.DELETE, site_id, widgetset_id,
                                widgetset=None, options=options, success=success, failure=failure)

    # MARK: - Theme
    def list_themes(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/themes'
        self.__fetch_list(url, options, success, failure)

    def get_theme(self, theme_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/themes/%s' % theme_id
        self.__get(url, options, success, failure)

    def apply_theme_to_site(self, site_id, theme_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/themes/%s/apply' % (site_id, theme_id)
        self.__post(url, options, success, failure)

    def uninstall_theme(self, theme_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/themes/%s' % theme_id
        self.__delete(url, options, success, failure)

    def export_site_theme(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/export_theme' % site_id
        self.__post(url, options, success, failure)

    # MARK: - Role
    def list_roles(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/roles'
        self.__fetch_list(url, options, success, failure)

    def __role_action(self, action, role_id=None, role=None, options=None, success=stub_callback,
                      failure=stub_callback):
        url = self.__api_url() + '/roles'
        if action != HTTPMethod.POST and role_id:
            url += '/' + str(role_id)
        self.__action('role', action, url, role, options, success, failure)

    def create_role(self, role, options=None, success=stub_callback, failure=stub_callback):
        self.__role_action(HTTPMethod.POST, role_id=None, role=role,
                           options=options, success=success, failure=failure)

    def get_role(self, role_id, options=None, success=stub_callback, failure=stub_callback):
        self.__role_action(HTTPMethod.GET, role_id, role=None,
                           options=options, success=success, failure=failure)

    def update_role(self, role_id, role, options=None, success=stub_callback, failure=stub_callback):
        self.__role_action(HTTPMethod.PUT, role_id, role,
                           options, success, failure)

    def delete_role(self, role_id, options=None, success=stub_callback, failure=stub_callback):
        self.__role_action(HTTPMethod.DELETE, role_id, role=None,
                           options=options, success=success, failure=failure)

    # MARK: - Permission
    def list_permissions(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/permissions'
        self.__fetch_list(url, options, success, failure)

    def __list_permissions_for_object(self, object_name, object_id, options=None, success=stub_callback,
                                      failure=stub_callback):
        url = self.__api_url() + '/%s/%s/permissions' % (object_name, object_id)
        self.__fetch_list(url, options, success, failure)

    def list_permissions_for_user(self, user_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_permissions_for_object(
            'users', user_id, options, success, failure)

    def list_permissions_for_site(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_permissions_for_object(
            'sites', site_id, options, success, failure)

    def list_permissions_for_role(self, role_id, options=None, success=stub_callback, failure=stub_callback):
        self.__list_permissions_for_object(
            'roles', role_id, options, success, failure)

    def grant_permission_to_site(self, site_id, user_id, role_id, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/permissions/grant' % site_id
        params = {'user_id': user_id, 'role_id': role_id}
        self.__post(url, params, success, failure)

    def grant_permission_to_user(self, user_id, site_id, role_id, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users/%s/permissions/grant' % user_id
        params = {'site_id': site_id, 'role_id': role_id}
        self.__post(url, params, success, failure)

    def revoke_permission_from_site(self, site_id, user_id, role_id, success=stub_callback, failiure=stub_callback):
        url = self.__api_url() + '/sites/%s/permissions/revoke' % site_id
        params = {'user_id': user_id, 'role_id': role_id}
        self.__post(url, params, success, failiure)

    def revoke_permission_from_user(self, user_id, site_id, role_id, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/users/%s/permissions/revoke' % user_id
        params = {'site_id': site_id, 'role_id': role_id}
        self.__post(url, params, success, failure)

    # MARK: - Log
    def list_logs(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/logs' % site_id
        self.__fetch_list(url, options, success, failure)

    def __log_action(self, action, site_id, log_id=None, log=None, options=None, success=stub_callback,
                     failure=stub_callback):
        url = self.__api_url() + '/sites/%s/logs' % site_id
        if action != HTTPMethod.POST and log_id:
            url += '/' + str(log_id)
        self.__action('log', action, url, log, options, success, failure)

    def create_log(self, site_id, log, options=None, success=stub_callback, failure=stub_callback):
        self.__log_action(HTTPMethod.POST, site_id, log_id=None,
                          log=log, options=options, success=success, failure=failure)

    def get_log(self, site_id, log_id, options=None, success=stub_callback, failure=stub_callback):
        self.__log_action(HTTPMethod.GET, site_id, log_id, log=None,
                          options=options, success=success, failure=failure)

    def update_log(self, site_id, log_id, log, options=None, success=stub_callback, failure=stub_callback):
        self.__log_action(HTTPMethod.PUT, site_id, log_id,
                          log, options, success, failure)

    def delete_log(self, site_id, log_id, options=None, success=stub_callback, failure=stub_callback):
        self.__log_action(HTTPMethod.DELETE, site_id, log_id, log=None,
                          options=options, success=success, failure=failure)

    def reset_logs(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/logs' % site_id
        self.__delete(url, options, success, failure)

    def export_logs(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/logs/export' % site_id
        self.__get(url, options, success, failure)

    # MARK: - FormattedText
    def list_formatted_texts(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/formatted_texts' % site_id
        self.__fetch_list(url, options, success, failure)

    def __formatted_text_action(self, action, site_id, formatted_text_id=None, formatted_text=None, options=None,
                                success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/formatted_text' % site_id
        if action != HTTPMethod.POST and formatted_text_id:
            url += '/' + str(formatted_text_id)
        self.__action('formatted_text', action, url,
                      formatted_text, options, success, failure)

    def create_formatted_text(self, site_id, formatted_text, options=None, success=stub_callback,
                              failure=stub_callback):
        self.__formatted_text_action(HTTPMethod.POST, site_id, formatted_text_id=None,
                                     formatted_text=formatted_text, options=options, success=success, failure=failure)

    def get_formatted_text(self, site_id, formatted_text_id, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__formatted_text_action(HTTPMethod.GET, site_id, formatted_text_id,
                                     formatted_text=None, options=options, success=success, failure=failure)

    def update_formatted_text(self, site_id, formatted_text_id, formatted_text, options=None, success=stub_callback,

                              failure=stub_callback):
        self.__formatted_text_action(
            HTTPMethod.PUT, site_id, formatted_text_id, formatted_text, options, success, failure)

    def delete_formatted_text(self, site_id, formatted_text_id, options=None, success=stub_callback,
                              failure=stub_callback):
        self.__formatted_text_action(HTTPMethod.DELETE, site_id, formatted_text_id,
                                     formatted_text=None, options=options, success=success, failure=failure)

    # MARK: - Stats
    def get_stats_provider(self, site_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/stats/provider' % site_id
        self.__get(url, options, success, failure)

    def __list_stats_for_target(self, site_id, target_name, object_name, start_date, end_date, options=None,
                                success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/sites/%s/stats/%s/%s' % (site_id, target_name, object_name)
        if not options:
            options = {}
        options['startDate'] = start_date
        options['endDate'] = end_date
        self.__fetch_list(url, options, success, failure)

    def __list_stats_for_path(self, site_id, object_name, start_date, end_date, options=None, success=stub_callback,
                              failure=stub_callback):
        self.__list_stats_for_target(site_id, target_name='path', object_name=object_name,
                                     start_date=start_date, end_date=end_date, options=options, success=success,
                                     failure=failure)

    def pageviews_for_path(self, site_id, start_date, end_date, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__list_stats_for_path(site_id, object_name='pageviews', start_date=start_date,
                                   end_date=end_date, options=options, success=success, failure=failure)

    def visits_for_path(self, site_id, start_date, end_date, options=None, success=stub_callback,
                        failure=stub_callback):
        self.__list_stats_for_path(site_id, object_name='visits', start_date=start_date,
                                   end_date=end_date, options=options, success=success, failure=failure)

    def __list_stats_for_date(self, site_id, object_name, start_date, end_date, options=None, success=stub_callback,
                              failure=stub_callback):
        self.__list_stats_for_target(site_id, target_name='date', object_name=object_name,
                                     start_date=start_date, end_date=end_date, options=options, success=success,
                                     failure=failure)

    def pageviews_for_date(self, site_id, start_date, end_date, options=None, success=stub_callback,
                           failure=stub_callback):
        self.__list_stats_for_date(site_id, object_name='pageviews', start_date=start_date,
                                   end_date=end_date, options=options, success=success, failure=failure)

    def visits_for_date(self, site_id, start_date, end_date, options=None, success=stub_callback,
                        failure=stub_callback):
        self.__list_stats_for_date(site_id, object_name='visits', start_date=start_date,
                                   end_date=end_date, options=options, success=success, failure=failure)

    # MARK: - Plugin
    def list_plugins(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/plugins'
        self.__fetch_list(url, options, success, failure)

    def get_plugin(self, plugin_id, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/plugins/%s' % plugin_id
        self.__get(url, options, success, failure)

    def __toggle_plugin(self, plugin_id, enable, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/plugins'
        if plugin_id != '*':
            url += '/' + plugin_id
        if enable:
            url += '/enable'
        else:
            url += '/disable'
        self.__post(url, options, success, failure)

    def enable_plugin(self, plugin_id, options=None, success=stub_callback, failure=stub_callback):
        self.__toggle_plugin(plugin_id, enable=True,
                             options=options, success=success, failure=failure)

    def disable_plugin(self, plugin_id, options=None, success=stub_callback, failure=stub_callback):
        self.__toggle_plugin(plugin_id, enable=False,
                             options=options, success=success, failure=failure)

    def enable_all_plugins(self, options=None, success=stub_callback, failure=stub_callback):
        self.__toggle_plugin(plugin_id='*', enable=True,
                             options=options, success=success, failure=failure)

    def disable_all_plugins(self, options=None, success=stub_callback, failure=stub_callback):
        self.__toggle_plugin(plugin_id='*', enable=False,
                             options=options, success=success, failure=failure)

    # MARK: - # V3
    # MARK: - Version
    def version(self, options=None, success=stub_callback, failure=stub_callback):
        url = self.__api_url() + '/version'

        def override_success(response):
            json_response = response.json()
            if json_response:
                self.endpoint_version = json_response.get('endpointVersion')
                self.__api_version = json_response.get('apiVersion')
            success(response)
        self.__get(url, options, override_success, failure)
