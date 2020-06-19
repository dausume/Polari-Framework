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
import logging
#Logic Nodes are components that are used to form Identity Nodes.  They come in four different types.
#the data, relator, operator, and proofer Node Types.
#Every node has a name, an execution order, a type, and a lock.
#A name must be unique within a Polari Database, the execution order controls at what step in a given
#identity or memory that.
class LogicNode:
    nodeTypes = ['data','relator','operator','proofer', 'restrictor']
    logFile = 'logs_LogicNodes.log'
    #Creates an anonymous Logic Node, used for dynamically creating or finding matches of existing Nodes.
    def __init__(self):
        self.name = None
        self.exeOrder = 0
        self.type = type
        self.lockNode = None

    def __init__(self, name, type):
        if(nodeTypes.contains(type)):
            self.name = name
            self.exeOrder = 0
            self.type = type
            self.lockNode = False

    def dataNodeInit(self, someData):
        self.data = someData
        self.lockNode = True

    #Defines a type of data and 
    def dataNodeInit(self, someData, dataId):
        self.data = someData
        self.dataId = dataId

    #takes in a left operand, an operator, and a right operand.
    def operatorNode(self, leftOp, operator, rightOp):
        self.operator = operationCommand
        self.leftOp = left
        self.rightOp = right

    #Exerts restrictions on what may enter or exist an identity based on Proofs attached to the data.
    def restrictionNode(self, proofing, sufficiency, necessity, Id, IO):
        if(proofCondition == 'Sufficent' or proofCondition == 'Necessary' or proofCondition == 'Absolute'):
            self.proofCondition = proofCondition
        if(sufficiencyMethod == 'Expansion' or sufficiencyMethod == 'EqualTerms' or sufficiencyMethod == 'Compression'):
            self.sufficiencyMethod = sufficiencyMethod
        if(necessityMethod == 'Constraining' or necessityMethod == 'Identical' or necessityMethod == 'Generalizing'):
            self.necessityMethod = necessityMethod
        if(IO == True or IO == False):
            self.IO = IO
        self.Id = Id

    #What kind of proofing does this exert, on what identity does it exert it, and does is this exerted on
    #an input coming into the identity/Logic Node or an output going out of the identity/Logic Node.
    def proofNode(self, proofing, sufficiency, necessity, Node, IO):
        if(proofCondition == 'Sufficent' or proofCondition == 'Necessary' or proofCondition == 'Absolute'):
            self.proofCondition = proofCondition
        if(sufficiencyMethod == 'Expansion' or sufficiencyMethod == 'EqualTerms' or sufficiencyMethod == 'Compression'):
            self.sufficiencyMethod = sufficiencyMethod
        if(necessityMethod == 'Constraining' or necessityMethod == 'Identical' or necessityMethod == 'Generalizing'):
            self.necessityMethod = necessityMethod
        if(IO == True or IO == False):
            self.IO = IO
        self.Node = Node

    #Takes in one or two input groups and outputs into one or two output groups
    #By combining many relator Nodes and feeding them into one another to output from a single node,
    #you can effectively create a many-input, single output, relationship.
    #By combining many relator Nodes and feeding them into each other while allowing single outputs
    #at each node, you can effectively create a single input, many output relationship.
    #Similarly by doing any number of combinations.
    #The input groups are divided into true and false, the true segment implies an input necessarily should be
    #within the true output group if no logic is performed on it.  The same applies to the false segment,
    #if there is no logic performed on it, it will automatedly be put into the false output group.
    #The trueLogic is an if statement that diverts true Inputs to false if found to be true.
    #The falseLogic is an if statement that diverts false inputs to true if found to be true.
    def relatorNode(self, trueInputGroup, trueLogic, falseLogic, falseInputGroup, trueOutputGroup, falseOutputGroup, relationType):
        self.trueInputGroup = trueInputGroup
        self.falseInputGroup = falseInputGroup
        self.trueOutputGroup = trueOutputGroup
        self.falseOutputGroup = falseOutputGroup
        self.trueLogic = trueLogic
        self.falseLogic = falseLogic
        self.relationType = relationType