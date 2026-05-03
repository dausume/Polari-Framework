from objectTreeDecorators import treeObject, treeObjectInit


class EquationDefinition(treeObject):
    """
    Configuration entity for a calculus / math equation.

    The `definition` field is a JSON blob with this shape:
      {
        "latexExpression": "\\int_0^1 \\sin(x) dx",
        "operationType": "integral_definite",
        "variableBindings": [
          { "symbol": "x", "source": { "type": "literal", "value": 0 } },
          { "symbol": "data", "source": { "type": "dataset_field", "datasetId": "...", "fieldPath": "..." } }
        ],
        "bounds": { "variable": "x", "lower": "0", "upper": "1" },
        "options": { "method": "trapezoidal" },
        "resultSpec": { "type": "scalar" | "expression" | "dataseries" }
      }

    See polariNoCode/equation_executor.py for the operation contract.
    """

    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}', manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class
        self.definition = definition
