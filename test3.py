"""Perfect PEP-257 compliant test file."""


def add_numbers(a: int, b: int) -> int:
    """Return the sum of two integers.
    
    Args:
        a: First integer.
        b: Second integer.
    
    Returns:
        Sum of a and b.
    """
    return a + b


def is_even(number: int) -> bool:
    """Check if a number is even.
    
    Args:
        number: Integer to check.
    
    Returns:
        True if even, False otherwise.
    
    Raises:
        ValueError: If number is negative.
    """
    if number < 0:
        raise ValueError("Number must be positive")
    return number % 2 == 0


class MathUtils:
    """Collection of mathematical utilities."""
    
    def factorial(self, n: int) -> int:
        """Calculate factorial of n.
        
        Args:
            n: Non-negative integer.
        
        Returns:
            Factorial value.
        
        Raises:
            ValueError: If n is negative.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return 1
        return n * self.factorial(n - 1)