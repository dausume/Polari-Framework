from dataTypes import *

class polariList(list):
    def jumpstart(self, treeObjInstance, varName):
        #print("eval of polariList before treeObjInstance is set: ", self)
        self.treeObjInstance = treeObjInstance
        self.varName = varName
        #print("eval of polariList after treeObjInstance is set: ", self)

    #Aside from directly setting the list, other methods of adding and taking away are not traced
    def append(self, value):
        if(type(value).__name__ in dataTypesPython and type(value) != list and type(value).__name__ !="polariList"):
            super().append(value)
            return
        #print("Appending to list on object instance ", self.treeObjInstance, " for variable ", self.varName, " with value ", value)
        for parentClass in self.treeObjInstance.__class__.__bases__:
            typeName = parentClass.__name__
            isManager = False
            isTreeObj = False
            #print("Parent class on treeObjInstance: ", parentClass.__name__)
            if(typeName == "managerObject"):
                #print("Set to append managerObj with value: ", value)
                isManager = True
                break
            elif(typeName == "treeObject"):
                #print("Set to append treeObj with value: ", value)
                isTreeObj = True
                break
        if(isManager and self.varName != "objectTyping" and self.treeObjInstance.complete):
            polyObj = self.treeObjInstance.getObjectTyping(self.treeObjInstance.__class__)
            selfTuple = self.treeObjInstance.getInstanceTuple(instance=self.treeObjInstance)
            if type(value) != list:
                if(value == None or value == []):
                    pass
                else:
                    accountedObjectType = False
                    accountedVariableType = False
                    if(type(value).__class__.__name__ in polyObj.objectReferencesDict):
                        accountedObjectType = True
                        #print("Class type ", type(value).__class__.__name__, " accounted for in object typing for ", self.treeObjInstance.__class__.__name__)
                        if(polyObj.objectReferencesDict[type(value).__class__.__name__]):
                            accountedVariableType = True
                            #print("Accounted for class type ", value, " as sole value in variable ", self.varName)
                    newpolyObj = self.treeObjInstance.getObjectTyping(classObj=value.__class__)
                    managerPolyTyping = self.treeObjInstance.getObjectTyping(self.treeObjInstance.__class__)
                    if(not accountedVariableType):
                        managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=self.varName)
                    ids = self.treeObjInstance.getInstanceIdentifiers(value)
                    valuePath = self.treeObjInstance.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                    if(valuePath == [selfTuple]):
                        #print("found an instance already in the objectTree at the correct location:", value)
                        #Do nothing, because the branch is already accounted for.
                        pass
                    elif(valuePath == None):
                        #add the new Branch
                        #print("Creating branch on manager for instance on variable ", self.varName, " for instance: ", value)
                        newBranch = tuple([newpolyObj.className, ids, value])
                        self.treeObjInstance.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                        #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                        if(self.treeObjInstance != value.branch):
                            value.branch = self.treeObjInstance
                        if(self.treeObjInstance != value.manager):
                            value.manager = self.treeObjInstance
                    else:
                        #add as a duplicate branch
                        #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                        duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
                        self.treeObjInstance.replaceOriginalTuple(self.treeObjInstance, originalPath=valuePath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                        #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                        if(value.branch != self.treeObjInstance):
                            value.branch = self.treeObjInstance
                        if(self.treeObjInstance != value.manager):
                            value.manager = self.treeObjInstance
            elif(type(value) == list or type(value).__name__ == "polariList"):
                #print("Accounting for setting elements in list on variable \'", self.varName, "\' on the manager object, with value ", value)
                #Adding a list of objects
                for inst in value:
                    #print("accounting for instance in list on manager with value: ", inst)
                    if(inst.__class__.__name__ in dataTypesPython):
                        #print("Skipped inst as a standard type")
                        continue
                    #print("accounting for instance in list on manager with value: ", inst)
                    accountedObjectType = False
                    accountedVariableType = False
                    if(type(inst).__class__.__name__ in polyObj.objectReferencesDict):
                        accountedObjectType = True
                        #print("Class type ", type(inst).__class__.__name__, " accounted for in object typing for ", self.treeObjInstance.__class__.__name__)
                        if(polyObj.objectReferencesDict[type(inst).__class__.__name__]):
                            accountedVariableType = True
                            #print("Accounted for class type ", inst, " as sole value in variable ", self.varName)
                    newpolyObj = self.treeObjInstance.getObjectTyping(classObj=inst.__class__)
                    managerPolyTyping = self.treeObjInstance.getObjectTyping(self.treeObjInstance.__class__)
                    if(not accountedVariableType):
                        managerPolyTyping.addToObjReferenceDict(referencedClassObj=inst.__class__, referenceVarName=self.varName)
                    ids = self.treeObjInstance.getInstanceIdentifiers(inst)
                    instPath = self.treeObjInstance.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, inst]))
                    if instPath == [selfTuple]:
                        #print("found an instance already in the objectTree at the correct location:", inst)
                        pass
                    elif instPath == None:
                        #print("Creating branch on manager for instance in list on variable ", self.varName, " for instance: ", inst)
                        newBranch = tuple([newpolyObj.className, ids, inst])
                        self.treeObjInstance.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                        #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                        if(self.treeObjInstance != inst.branch):
                            inst.branch = self.treeObjInstance
                        if(self.treeObjInstance != inst.manager):
                            inst.manager = self.treeObjInstance
                    else:
                        #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                        duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(instPath)]) 
                        self.treeObjInstance.replaceOriginalTuple(self.treeObjInstance, originalPath = instPath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                        #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                        if(self.treeObjInstance != inst.branch):
                            inst.branch = self.treeObjInstance
                        if(self.treeObjInstance != inst.manager):
                            inst.manager = self.treeObjInstance
            else:
                #print('Setting attribute to a value: ', value)
                #print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', self.varName, 'On object: ', self.treeObjInstance)
                newpolyObj = self.treeObjInstance.getObjectTyping(classObj=value.__class__)
                managerPolyTyping = self.treeObjInstance.getObjectTyping(self.treeObjInstance.__class__)
                managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=self.varName)
                #print('Setting attribute on manager using a new polyTyping: ', newpolyObj.className, '; and set manager\'s new reference dict: ', managerPolyTyping.objectReferencesDict)
                print(newpolyObj.className, 'object placed on manager ', self.treeObjInstance,' it\'s referenceDict after allocation is: ', newpolyObj.objectReferencesDict)
                #if(self.identifiersComplete(value)):
                ids = self.treeObjInstance.getInstanceIdentifiers(value)
                valuePath = self.treeObjInstance.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                if(valuePath == [selfTuple]):
                    #print("found an instance already in the objectTree at the correct location:", value)
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    #print("Creating branch on manager for variable ", self.varName," for instance: ", value)
                    newBranch = tuple([newpolyObj.className, ids, value])
                    self.treeObjInstance.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(self.treeObjInstance != value.branch):
                        value.branch = self.treeObjInstance
                    if(self.treeObjInstance != value.manager):
                        value.manager = self.treeObjInstance
                else:
                    #add as a duplicate branch
                    #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                    duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self.treeObjInstance, originalPath=valuePath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(self.treeObjInstance != value.branch):
                        value.branch = self.treeObjInstance
                    if(self.treeObjInstance != value.manager):
                        value.manager = self.treeObjInstance
        if(isTreeObj):
            selfPolyObj = self.treeObjInstance.manager.getObjectTyping(self.treeObjInstance.__class__)
            selfIds = self.treeObjInstance.manager.getInstanceIdentifiers(value)
            selfTuple = self.treeObjInstance.manager.getInstanceTuple(self.treeObjInstance)
            selfPath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=selfTuple)
            #Handles the case where the current treeObject already exists in the current manager's Tree.
            if(selfPath != None):
                #print("Found appropriate path for treeObject")
                if value == None:
                    pass
                elif(type(value).__name__ == "list" or type(value).__name__ == "polariList"):
                    print("Going through list variable assignment for var ", self.varName ," post-init on treeObject using list ", value)
                    #Adding a list of objects
                    for inst in value:
                        accountedObjectType = False
                        accountedVariableType = False
                        if(type(inst).__class__.__name__ in selfPolyObj.objectReferencesDict):
                            accountedObjectType = True
                            print("Class type ", type(inst).__class__.__name__, " accounted for in object typing for ", self.treeObjInstance.__class__.__name__)
                            if(selfPolyObj.objectReferencesDict[type(inst).__class__.__name__]):
                                accountedVariableType = True
                                print("Accounted for class type ", inst, " as sole value in variable ", self.varName)
                        newpolyObj = self.treeObjInstance.manager.getObjectTyping(classObj=inst.__class__)
                        managerPolyTyping = self.treeObjInstance.manager.getObjectTyping(self.treeObjInstance.__class__)
                        if(not accountedVariableType):
                            managerPolyTyping.addToObjReferenceDict(referencedClassObj=inst.__class__, referenceVarName=self.varName)
                        ids = self.treeObjInstance.manager.getInstanceIdentifiers(inst)
                        instPath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                        if instPath == None:
                            #print("found an instance with no existing branch, now creating branch on manager: ", inst)
                            newBranch = tuple([inst.__class__.__name__, ids, inst])
                            self.treeObjInstance.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self.treeObjInstance != inst.branch):
                                inst.branch = self.treeObjInstance
                            if(self.treeObjInstance.manager != inst.manager):
                                inst.manager = self.treeObjInstance.manager
                        elif len(instPath) <= len(selfPath) + 1:
                            #print("found an instance already in the objectTree at the correct location:", inst)
                            pass
                        else:
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                            duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                            self.treeObjInstance.manager.replaceOriginalTuple(self.treeObjInstance.manager, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self.treeObjInstance != inst.branch):
                                inst.branch = self.treeObjInstance
                            if(self.treeObjInstance.manager != inst.manager):
                                inst.manager = self.treeObjInstance.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
                    #All other cases should have been eliminated, this should be dealing with object instances
                    #that have a treeObject base and are non-ignored, being assigned to a single variable.
                    else:
                        #print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.treeObjInstance.manager.getInstanceIdentifiers(value)
                        valuePath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if(valuePath == None):
                            #add the new Branch
                            #print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.treeObjInstance.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self.treeObjInstance != value.branch):
                                value.branch = self.treeObjInstance
                            if(self.treeObjInstance.manager != value.manager):
                                value.manager = self.treeObjInstance.manager
                        elif len(valuePath) <= len(selfPath) + 1:
                            #print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        else:
                            #add as a duplicate branch
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.treeObjInstance.replaceOriginalTuple(self.treeObjInstance.manager, originalPath=valuePath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self.treeObjInstance != value.branch):
                                value.branch = self.treeObjInstance
                            if(self.treeObjInstance.manager != value.manager):
                                value.manager = self.treeObjInstance.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
                #Handles the case where a single variable is being set.
                else:
                    #print("Appending to list post-init on treeObject", self.treeObjInstance, " using value ", value)
                    accountedObjectType = False
                    accountedVariableType = False
                    if(type(value).__class__.__name__ in selfPolyObj.objectReferencesDict):
                        accountedObjectType = True
                        #print("Class type ", type(value).__class__.__name__, " accounted for in object typing for ", self.treeObjInstance.__class__.__name__)
                        if(selfPolyObj.objectReferencesDict[type(value).__class__.__name__]):
                            accountedVariableType = True
                            #print("Accounted for class type ", value, " as sole value in variable ", self.varName)
                    newpolyObj = self.treeObjInstance.manager.getObjectTyping(classObj=value.__class__)
                    managerPolyTyping = self.treeObjInstance.manager.getObjectTyping(self.treeObjInstance.manager.__class__)
                    if(not accountedVariableType):
                        managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=self.varName)
                    ids = self.treeObjInstance.manager.getInstanceIdentifiers(value)
                    valuePath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                    #print('Setting attribute to a value: ', value)
                    #print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', name, 'On object: ', self)
                    newpolyObj = self.treeObjInstance.manager.getObjectTyping(value.__class__)
                    if(type(value).__name__ == "list" or type(value).__name__ == "polariList"):
                        #Adding a list of objects
                        for inst in value:
                            #print('Adding one object as element in a list variable, ', name ,' to the manager with value: ', inst)
                            #if(self.identifiersComplete(inst)):
                            ids = self.treeObjInstance.manager.getInstanceIdentifiers(inst)
                            instPath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                            #Case where the existing tuple is at the same level as this object or a lower object, in this case we place a duplicate while leaving the original alone.
                            #Case where the object has no existing tuple in the tree.
                            if instPath == None:
                                #print("found an instance with no existing branch, now creating branch on manager: ", inst)
                                newBranch = tuple([inst.__class__.__name__, ids, inst])
                                self.treeObjInstance.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                                #Make sure the new branch has the current manager set on it.
                                if(self.manager != inst.manager):
                                    inst.manager = self.manager
                            elif len(instPath) <= len(selfPath) + 1:
                                #print("found an instance already in the objectTree at the correct location:", inst)
                                pass
                            else:
                                #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                                duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                                self.treeObjInstance.manager.replaceOriginalTuple(self.treeObjInstance.manager, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                                #Make sure the new branch has the current manager set on it.
                                if(self.treeObjInstance.manager != inst.manager):
                                    inst.manager = self.treeObjInstance.manager
                                #TODO make a function that swaps any branching on the original tuple to be on the new location.
                    else:
                        #print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.treeObjInstance.manager.getInstanceIdentifiers(value)
                        valuePath = self.treeObjInstance.manager.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if(valuePath == None):
                            #add the new Branch
                            #print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.treeObjInstance.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager set on it.
                            if(self.treeObjInstance.manager != value.manager):
                                value.manager = self.treeObjInstance.manager
                        elif(len(valuePath) <= len(selfPath) + 1):
                            #print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        else:
                            #add as a duplicate branch
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.treeObjInstance.manager.replaceOriginalTuple(self.treeObjInstance, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager set on it.
                            if(self.treeObjInstance.manager != value.manager):
                                value.manager = self.treeObjInstance.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
            #else:
                #print("selfPath was not found in tree for object ", self.treeObjInstance)
        #print("appending on polariList object")
        #print("instance that this polariList instance is attached to is: ", self.treeObjInstance)
        super().append(value)

    def __len__(self):
        return super().__len__()

    def pop(self, value):
        super().pop(value)

    def __setitem__(self, key, value):
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        return super().__delitem__(key)