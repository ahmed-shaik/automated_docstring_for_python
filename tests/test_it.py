
"""Module containing various functions and classes.

This module provides utility functions and classes for different operations.
"""

def add(a, b):
    """
    add function.




    
    Args:
        a: Required parameter.
        b: Required parameter.
    
    Returns:
        Any: The result of the operation.
    """
    return a + b






def calculate_total(items, discount=0.1):
    """
    calculate_total function.





    
    Args:
        items: Optional parameter with a default value.
        discount: Required parameter.
    
    Returns:
        Any: The result of the operation.    """
    total = sum(items)





    return total * (1 - discount)

class Calculator:
    """
    Calculator class.
    """
    def multiply(self, x, y):
        """
        multiply function.


        
        Args:
            x: Required parameter.
            y: Required parameter.
        
        Returns:
            Any: The result of the operation.
        """
        return x * y





    
    def power(self, base, exponent):
        """
        power function.


        
        Args:
            base: Required parameter.
            exponent: Required parameter.
        
        Returns:
            Any: The result of the operation.
        """
        result = 1





        for _ in range(exponent):
            result *= base
        return result

def process_data(data: list) -> dict:
    """
    process_data function that returns dict.



    
    Args:
        data (list): Required parameter.
    
    Returns:
        dict: The processed result.
    """
    return {"processed": len(data)}