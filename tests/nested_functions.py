"""Module containing various functions and classes.

This module provides utility functions and classes for different operations.
"""

def outer(a, b):
    """
    outer function.

    
    Args:
        a: Required parameter.
        b: Required parameter.
    
    Returns:
        Any: The result of the operation.
    """
    result = a + b


    def inner(x):
        """
        inner function.

        
        Args:
            x: Required parameter.
        
        Returns:
            Any: The result of the operation.
        """
        return x * 2

    return inner(result)