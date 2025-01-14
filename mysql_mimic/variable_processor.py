from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from mypy.ipc import TracebackType
from sqlglot import expressions as exp

from mysql_mimic.intercept import value_to_expression, expression_to_value
from mysql_mimic.variables import Variables


@dataclass
class SessionContext:
    """
    Contains properties of the current session relevant to setting system variables.

    Args:
        connection_id: connection id for the session.
        external_user: the username from the identity provider.
        current_user: username of the authorized user.
        version: MySQL version.
        database: MySQL database name.
        variables: dictionary of session variables.
        timestamp: timestamp at the start of the current query.
    """

    connection_id: int
    external_user: str
    current_user: str
    version: str
    database: str
    variables: Variables
    timestamp: datetime


variable_constants = {
    "CURRENT_USER",
    "CURRENT_TIME",
    "CURRENT_TIMESTAMP",
    "CURRENT_DATE",
}


class VariableProcessor:
    """
    This class modifies the query in two ways:
        1. Processing SET_VAR hints for system variables in the query text
        2. Replacing certain MySQL functions with their internal representations based on the session context.
    Once the context manager exits, any system variables modified within the query context are reset to their
    original values.
    """

    def __init__(self, session: SessionContext, expression: exp.Expression):
        self._session = session
        self._expression = expression

        # Stores the original system variable values.
        self._orig: dict[str, str] = {}

        # Information functions.
        # These will be replaced in the AST with their corresponding values.
        self._functions = {
            "CONNECTION_ID": lambda: session.connection_id,
            "USER": lambda: session.external_user,
            "CURRENT_USER": lambda: session.current_user,
            "VERSION": lambda: session.version,
            "DATABASE": lambda: session.database,
            "NOW": lambda: session.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "CURDATE": lambda: session.timestamp.strftime("%Y-%m-%d"),
            "CURTIME": lambda: session.timestamp.strftime("%H:%M:%S"),
        }
        # Synonyms
        self._functions.update(
            {
                "SYSTEM_USER": self._functions["USER"],
                "SESSION_USER": self._functions["USER"],
                "SCHEMA": self._functions["DATABASE"],
                "CURRENT_TIMESTAMP": self._functions["NOW"],
                "LOCALTIME": self._functions["NOW"],
                "LOCALTIMESTAMP": self._functions["NOW"],
                "CURRENT_DATE": self._functions["CURDATE"],
                "CURRENT_TIME": self._functions["CURTIME"],
            }
        )

    def __enter__(self) -> Variables:
        assignments = self._get_var_assignments()
        self._orig = {k: self._session.variables.get(k) for k in assignments}
        for k, v in assignments.items():
            self._session.variables.set(k, v)
        self._replace_variables()
        return self._session.variables

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        for k, v in self._orig.items():
            self._session.variables.set(k, v)

    def _get_var_assignments(self) -> Dict[str, str]:
        """Returns a dictionary of system variables to replace, as indicated by SET_VAR hints."""
        hints = self._expression.find_all(exp.Hint)
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

    def _replace_variables(self) -> None:
        """Replaces certain system variables with information provided from the session context."""
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
            value = self._session.variables.get(node.name)
            new_node = value_to_expression(value)

        if (
            new_node
            and isinstance(node.parent, exp.Select)
            and node.arg_key == "expressions"
        ):
            new_node = exp.alias_(new_node, exp.to_identifier(node.sql()))

        return new_node or node
