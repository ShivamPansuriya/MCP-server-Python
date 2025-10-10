# function_executor_typed.py

from types import FunctionType
import inspect

# User data mapping (per-user configuration)
user_data = {
    "1": {"name": "a", "function_args": ["alpha"]},
    "2": {"name": "a", "function_args": ["x", "y"]},
    "3": {"name": "abcd", "function_args": [1, 2, 3]},
}

# Function definitions to create dynamically
# Values determine both number of arguments and their types
function_definitions = {
    "a": ["param1"],
    "ab": ["p1", "p2"],
    "abcd": [1, 2, 3]  # should create function with (int, int, int)
}


def infer_type(value):
    """Infer the Python type of a value for annotation."""
    return type(value) if value is not None else str


def make_function(name, arg_values):
    """
    Dynamically create a strict function with typed arguments based on arg_values.
    Example:
        arg_values = [1, 2, 3] → (int, int, int)
        arg_values = ["a", "b"] → (str, str)
    """
    # Generate parameter names: a1, a2, a3...
    arg_names = [f"a{i+1}" for i in range(len(arg_values))]

    # Infer argument types
    annotations = [infer_type(v) for v in arg_values]

    # Define template (core logic)
    def template(**kwargs):
        print(f'Executing function "{name}" with arguments:')
        for k, v in kwargs.items():
            print(f"  {k}: {v} ({type(v).__name__})")

    # Build function signature with correct annotations
    params = [
        inspect.Parameter(
            arg_names[i],
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=annotations[i]
        )
        for i in range(len(arg_names))
    ]

    sig = inspect.Signature(params)
    template.__signature__ = sig  # type: ignore
    template.__name__ = name
    template.__doc__ = f"Dynamically created typed function '{name}'"

    # Enforce signature strictly at runtime
    def wrapper(*args, **kwargs):
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return template(**bound_args.arguments)

    wrapper.__name__ = name
    wrapper.__signature__ = sig  # type: ignore
    return wrapper


# Dynamically create and register functions
function_map = {
    name: make_function(name, values)
    for name, values in function_definitions.items()
}


def execute_function(user_id, tool_name):
    user = user_data.get(user_id)
    if not user:
        print(f"No data found for user {user_id}")
        return

    if user["name"] != tool_name:
        print(f"Tool name mismatch for user {user_id}")
        return

    func = function_map.get(tool_name)
    if not func:
        print(f"Function '{tool_name}' not found")
        return

    args = user["function_args"]
    func(*args)


# Example Execution
if __name__ == "__main__":
    execute_function("1", "a")     # → (str)
    execute_function("3", "abcd")  # → (int, int, int)
