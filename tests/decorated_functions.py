"""Module containing various functions and classes.

This module provides utility functions and classes for different operations.
"""

def my_decorator(func):
    """
my_decorator function.





Args:
    func: Required parameter.

Returns:
    Any: The result of the operation.
    """

    def wrapper(*args, **kwargs):
        """
        wrapper function.




        
        Args:
            args: Variable number of positional arguments.
            kwargs: Variable number of keyword arguments.
        
        Returns:
            Any: The result of the operation.
        """
        return func(*args, **kwargs)





    return wrapper


@my_decorator
def greet(name):
    """
    greet function.




    
    Args:
        name: Required parameter.
    
    Returns:
        Any: The result of the operation.
    """
    return f"Hello {name}"