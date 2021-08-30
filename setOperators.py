#Takes two sets of arbitrary instances in the format of a dictionary
#with string ids as keys and instances as values, and returns a set
#that is the intersection of those two Sets
def instanceSetIntersection(setOne, setTwo):
    pass

def instanceSetUnion(setOne, setTwo):
    pass

    #TODO Add functionality to sort retrievableInstances into different sets
    #of variables with allowed read access.
    #
    #Returns a list of tuples [([restricted Vars List],[List Of Instances]), dataSetTuple2, ...]
def segmentDataSetsByPermissions(api, instances, permissions, className, CRUDEselection):
    dataSetsList = []
    #Get the dataSets
    if(CRUDEselection == "C"):
        permissionTupleQueries = permissions["C"][className]
    elif(CRUDEselection == "R"):
        permissionTupleQueries = permissions["R"][className]
        for permTuple in permissionTupleQueries:
            dataSetsList.append(api.manager.getListOfInstancesByAttributes(className=className, attributeQueryDict=permTuple[1]))
    elif(CRUDEselection == "U"):
        permissionTupleQueries = permissions["U"][className]
    elif(CRUDEselection == "D"):
        permissionTupleQueries = permissions["D"][className]
    elif(CRUDEselection == "E"):
        permissionTupleQueries = permissions["E"][className]
    pass

