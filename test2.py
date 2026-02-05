"""Test file with missing docstrings only."""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def subtract(x, y):
    """Subtract y from x."""
    return x - y


def multiply():
    """
    multiply function.
    
    Returns:
        Any: The result of the operation.
    """
    return 10 * 5


class Calculator:
    """Simple calculator class."""
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ZeroDivisionError
        return a / b
    
    def power(self, x, n):
        """
        power function.
        
        Args:
            x: Required parameter.
            n: Required parameter.
        
        Returns:
            Any: The result of the operation.
        """
        return x ** n


def no_docs_here():
    """
    no_docs_here function.
    
    Returns:
        Any: The result of the operation.
    """
    return None