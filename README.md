# mt-data-api-sdk-python
A port of [mt-data-api-sdk-swift](https://github.com/movabletype/mt-data-api-sdk-swift).

# Install

```bash
$ pip install mt-data-api
```

# Usage
```python

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

username = 'admin'
password = 'password'
client.authentication(username, password, remember=False,
                      success=success, failure=failure)

client.endpoints(success, failure)
client.list_sites(success=success, failure=failure)

site_id = 1
entry = {'title': 'test entry'}
client.create_entry(site_id, entry, success=success, failure=failure)
```

# License & Copyright
```
The MIT License (MIT)

Copyright (c) 2015 Six Apart, Ltd.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```
