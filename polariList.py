class polariList(list):
    def jumpstart(self, treeObjInstance):
        #print("eval of polariList before treeObjInstance is set: ", self)
        self.treeObjInstance = treeObjInstance
        #print("eval of polariList after treeObjInstance is set: ", self)

    #Aside from directly setting the list, other methods of adding and taking away are not traced
    def append(self, value):
        #if(type(value) == polariList):
        #    value = list(value)
        #if(type(value) != list and type(value) != polariList):
        #    value = [value]
        print("appending on polariList object")
        print("instance that this polariList instance is attached to is: ", self.treeObjInstance)
        super().append(value)

    def __len__(self):
        return super().__len__()

    def pop(self, value):
        super().pop(value)

    def __setitem__(self, key, value):
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        return super().__delitem__(key)