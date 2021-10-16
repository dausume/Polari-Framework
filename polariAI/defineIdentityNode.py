#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
class identityNode():
    def __init__(self, name):
        self.name = name
        self.identitiesFileLocation = None
        #A valid sub-set of the existing nodes in the Identity, such that the set of nodes can be
        #ordered and processed into coherent executable code specific to a given situation.  A single
        #specifier, given that it is complete and process, should be able to produce a standalone
        #executable with testable inputs and outputs.
        self.specifiers = []
        #A set of Operator, Relator, Data, and Proofing Logic Nodes which collapse into specific states
        #and overall hold the defininition of WHAT an identity IS. 
        #(States are held in data as specifier instances).
        self.internalLogicNodes = []
        #A set of Operator, Relator, Data, and Proofing Logic Nodes which collapse into specific states
        #and overall define how this Identity can be related to other identities.
        #Ultimately defining HOW an Identity can be USED. 
        self.externalLogicNodes = []
        #Holds Identities that are logical equivolents to a Logic Node or set of Nodes
        #these can replace the original logic nodes and act as substitutes for them.
        self.internalIdentityNodes = []
        #Holds Identities that are capable of having any kind of Proofing Relationship with any
        #of the Identities' input or output nodes.
        self.externalIdentityNodes = []

    def __setattr__(self, key, value):
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
        super(Point, self).__setattr__(key, value)

    def isComplete(self):
        if(self.proofCondition != None and self.sufficiencyMethod != None and self.necessityMethod != None):
            return True
        else:
            return False

    def setProofingLogic(self, proofCondition):
        if(proofCondition == 'Sufficent' or proofCondition == 'Necessary' or proofCondition == 'Absolute'):
            self.proofCondition = proofCondition

    def setSufficiencyMethod(self, sufficiencyMethod):
        if(sufficiencyMethod == 'Expansion' or sufficiencyMethod == 'EqualTerms' or sufficiencyMethod == 'Compression'):
            self.sufficiencyMethod = sufficiencyMethod

    def setNecessityMethod(self, necessityMethod):
        if(necessityMethod == 'Constraining' or necessityMethod == 'Identical' or necessityMethod == 'Generalizing'):
            self.necessityMethod = necessityMethod