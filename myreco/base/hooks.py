# MIT License

# Copyright (c) 2016 Diogo Dutra

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from myreco.exceptions import UnauthorizedError
from falcon import HTTP_FORBIDDEN


class AuthorizationHook(object):
    def __init__(self, authorizer_func, realm):
        self.authorizer = authorizer_func
        self.realm = realm

    def __call__(self, req, resp, resource, params):
        authorization = req.auth
        if authorization is None:
            raise UnauthorizedError('Authorization header is required', self.realm)

        basic_str = 'Basic '
        if authorization.startswith(basic_str):
            authorization = authorization.replace(basic_str, '')

        session = req.context['session']
        authorization = self.authorizer(session, authorization,
            req.uri_template, req.path, req.method)

        if authorization is None:
            raise UnauthorizedError('Invalid authorization', self.realm)

        elif authorization is False:
            raise UnauthorizedError(
                'Please refresh your authorization', self.realm, HTTP_FORBIDDEN)
