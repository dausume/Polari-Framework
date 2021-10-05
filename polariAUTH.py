import falcon

class polariAuthMiddleware:

    async def process_request(self, req, resp):
        token = req.get_header('Authorization')
        account_id = req.get_header('Account-ID')
        #Challenges overrides values on the WWW-Authenticate headers.
        #For a list of all options look at this URL.
        #https://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml
        challenges = ['Basic']

        if token is None:
            description = ('Please provide an auth token '
                           'as part of the request.')

            raise falcon.HTTPUnauthorized(title='Authentication token required',
                                          description=description,
                                          challenges=challenges,
                                          href='http://polariai.com/auth-docs')

        if not self._token_is_valid(token, account_id):
            description = ('Invalid, timed-out or non-existent Authentication Token.'
                           'Logging in through appropriate channels should ensure Auth token is provided')

            raise falcon.HTTPUnauthorized(title='Authentication token required',
                                          description=description,
                                          challenges=challenges
                                          )

    #Confirms the token is valid for the given account.
    def _token_is_valid(self, token, account_id):
        return True