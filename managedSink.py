#Creates an instance for defining callouts to other existing Polari Nodes or external
#systems such as search engines
class SinkAdapter:
    #Example of things that can be indicated as sinks and used often
    localNetworkSinks = {
        'localAngularFrontendServer': 'IP_ofSysOnSameRouter/localhost:3000/',
        'localPolariNodeServer': 'IP_ofSysOnSameRouter/localhost:8000/',
        'googleSearchEngine': 'http://www.google.com'
    }

    reqTypes = {
        #Basic CRUD
        'Create',
        'Read',
        'Update',
        'Delete',
        #Special callout used for calling of / executing functions on another Polari Node.
        'Operation'
    }

    async def __call__(self, reqType, req, resp, locSinkURL):
        if(not reqType in reqTypes):
            print('Passed invalid value for reqType parameter.')
        params = {'q': req.get_param('q', True)}
        if(reqType == 'Read'):
            async with httpx.AsyncClient() as client:
                result = await client.get(locSinkURL, params=params)

        resp.status = result.status_code
        resp.content_type = result.headers['content-type']
        resp.text = result.text