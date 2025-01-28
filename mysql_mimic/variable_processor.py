from contextlib import contextmanager
from typing import Dict, Mapping, Generator, MutableMapping, Any

from sqlglot import expressions as exp

from mysql_mimic.intercept import value_to_expression, expression_to_value

variable_constants = {
    "CURRENT_USER",
    "CURRENT_TIME",
    "CURRENT_TIMESTAMP",
    "CURRENT_DATE",
}


def _get_var_assignments(expression: exp.Expression) -> Dict[str, str]:
    """Returns a dictionary of session variables to replace, as indicated by SET_VAR hints."""
    hints = expression.find_all(exp.Hint)
    if not hints:
        return {}

    assignments = {}

    # Iterate in reverse order so higher SET_VAR hints get priority
    for hint in reversed(list(hints)):
        set_var_hint = None

        for e in hint.expressions:
            if isinstance(e, exp.Func) and e.name == "SET_VAR":
                set_var_hint = e
                for eq in e.expressions:
                    assignments[eq.left.name] = expression_to_value(eq.right)

        if set_var_hint:
            set_var_hint.pop()

        # Remove the hint entirely if SET_VAR was the only expression
        if not hint.expressions:
            hint.pop()

    return assignments


class VariableProcessor:
    """
    This class modifies the query in two ways:
        1. Processing SET_VAR hints for system variables in the query text
        2. Replacing functions in the query with their replacements defined in the functions argument.
    original values.
    """

    def __init__(
        self, functions: Mapping, variables: MutableMapping, expression: exp.Expression
    ):
        self._functions = functions
        self._variables = variables
        self._expression = expression

        # Stores the original system variable values.
        self._orig: Dict[str, Any] = {}

    @contextmanager
    def set_variables(self) -> Generator[exp.Expression, None, None]:
        assignments = _get_var_assignments(self._expression)
        self._orig = {k: self._variables.get(k) for k in assignments}
        for k, v in assignments.items():
            self._variables[k] = v

        self._replace_variables()

        yield self._expression

        for k, v in self._orig.items():
            self._variables[k] = v

    def _replace_variables(self) -> None:
        """Replaces certain functions in the query with literals provided from the mapping in _functions,
        and session parameters with the values of the session variables.
        """
        if isinstance(self._expression, exp.Set):
            for setitem in self._expression.expressions:
                if isinstance(setitem.this, exp.Binary):
                    # In the case of statements like: SET @@foo = @@bar
                    # We only want to replace variables on the right
                    setitem.this.set(
                        "expression",
                        setitem.this.expression.transform(self._transform, copy=True),
                    )
        else:
            self._expression.transform(self._transform, copy=False)

    def _transform(self, node: exp.Expression) -> exp.Expression:
        new_node = None

        if isinstance(node, exp.Func):
            if isinstance(node, exp.Anonymous):
                func_name = node.name.upper()
            else:
                func_name = node.sql_name()
            func = self._functions.get(func_name)
            if func:
                value = func()
                new_node = value_to_expression(value)
        elif isinstance(node, exp.Column) and node.sql() in variable_constants:
            value = self._functions[node.sql()]()
            new_node = value_to_expression(value)
        elif isinstance(node, exp.SessionParameter):
            value = self._variables.get(node.name)
            new_node = value_to_expression(value)

        if (
            new_node
            and isinstance(node.parent, exp.Select)
            and node.arg_key == "expressions"
        ):
            new_node = exp.alias_(new_node, exp.to_identifier(node.sql()))

        return new_node or node
