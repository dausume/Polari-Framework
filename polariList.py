class polariList(list):
    #Aside from directly setting the list, other methods of adding and taking away are not traced
    def append(self, value):
        return list.append(object=value)

    def pop(self, value):
        return list.append(object=value)

    def __setitem__(self, key, value):
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        return super().__delitem__(key)